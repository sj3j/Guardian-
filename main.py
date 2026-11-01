import os
from datetime import datetime, timedelta
import asyncio
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from dotenv import load_dotenv

from background import (
    is_admin,
    is_target_admin,
    check_badwords,
    check_nightmarecall,
    RegBotinfo,
    has_link,
    has_username,
    has_tag,
    warn_and_delete,
    HELP_TEXT,
)
from database import (
    init_db,
    get_chat_locks,
    set_chat_lock,
    set_all_chat_locks,
    save_muted_member,
    remove_muted_member,
    get_muted_members,
    save_banned_member,
    remove_banned_member,
    get_banned_members,
    LOCK_COLUMNS,
    LOCK_ALIASES,
)

load_dotenv()

# Initialize SQLite database
init_db()

try:
    os.system("clear" if os.name != "nt" else "cls")
except Exception:
    pass

print("\n- Nightmare: Hi Fenix, I'm Night how can I help you today?\n")

bot = Client(
    "ai",
    api_id=os.getenv("api_id"),
    api_hash=os.getenv("api_hash"),
    bot_token=os.getenv("BOT_TOKEN"),
)


@bot.on_message(filters.command("secret") & filters.private)
async def secret_command(client, message):
    RegBotinfo(message)
    msg = await message.reply("it's E-chan ❤️!")
    i = 0
    while i < 10:
        await msg.edit("-How are you shawty?")
        await asyncio.sleep(0.3)
        await msg.edit("- How was ur day?🤍..")
        await asyncio.sleep(0.3)
        await msg.edit("- Bakayaruu!...")
        await asyncio.sleep(0.3)
        await msg.edit("- I miss ya ❤️‍🩹...")
        await asyncio.sleep(0.4)
        await msg.edit("- Don't forget that I Wolf u!❤️‍🩹...")
        await asyncio.sleep(0.3)
        await msg.edit("- always be good!❤️‍🩹...")
        await asyncio.sleep(0.3)
        await msg.edit("- U R My ∞!❤️‍🩹...")
        await asyncio.sleep(0.3)
        await msg.edit("- don't be ever be a stranger!🖤...")
        await asyncio.sleep(0.3)
        i += 1


@bot.on_message(filters.command("start") & filters.private)
async def start_private(client, msg):
    await msg.reply(
        "👋 **أهلاً بك في بوت نايت (Guardian)!**\n\n"
        "أنا بوت حماية وإدارة المجموعات ومساعد ذكي مدعوم بنموذج Google Gemini 🛡️🤖\n\n"
        "للاطلاع على جميع الأوامر ودليل الاستخدام، أرسل: `/help` أو `مساعدة`",
        disable_web_page_preview=True,
    )


@bot.on_message(
    (filters.command(["help", "مساعدة"]) | filters.regex(r"^(?i)(help|مساعدة)$"))
    & filters.private
)
async def help_private(client, msg):
    await msg.reply(HELP_TEXT, disable_web_page_preview=True)


@bot.on_message(filters.command("start") & filters.group)
async def start_group(client, msg):
    await msg.reply("أهلاً، أنا نايت بوت ذكاء اصطناعي وحماية كروبات، \n\n- `BY: @sj3js`")


@bot.on_message(filters.command(["help", "مساعدة"]) & filters.group)
async def help_group(client, msg):
    await msg.reply(HELP_TEXT, disable_web_page_preview=True)


@bot.on_message(filters.command(["Arise", "arise"]) & filters.group)
async def list_muted_and_banned(client, msg):
    chat_id = msg.chat.id
    muted = get_muted_members(chat_id)
    banned = get_banned_members(chat_id)

    response = "📋 **قائمة الأعضاء المقيدين في هذه المجموعة:**\n\n"

    if muted:
        response += "📌 **الأعضاء المكتومين:**\n"
        for user_id, (name, until) in muted.items():
            if until:
                rem = (until - datetime.now()).total_seconds()
                if rem > 0:
                    if rem >= 3600:
                        remaining = f"{rem // 3600:.0f} ساعة"
                    else:
                        remaining = f"{rem // 60:.0f} دقيقة"
                else:
                    remaining = "منتهي"
            else:
                remaining = "دائم"
            response += f"- <a href='tg://user?id={user_id}'>{name}</a>: متبقي ({remaining})\n"
    else:
        response += "لا يوجد أعضاء مكتومين حاليًا.\n"

    response += "\n"

    if banned:
        response += "🚫 **الأعضاء المطرودين / المحظورين:**\n"
        for user_id, name in banned.items():
            response += f"- <a href='tg://user?id={user_id}'>{name}</a>\n"
    else:
        response += "لا يوجد أعضاء مطرودين حاليًا.\n"

    await msg.reply(response, disable_web_page_preview=True)


@bot.on_message(filters.group & filters.new_chat_members)
async def handle_new_members(client, msg):
    chat_id = msg.chat.id
    locks = get_chat_locks(chat_id)
    if not locks.get("bots"):
        return

    # Check if newly added members are bots
    for user in msg.new_chat_members:
        if user.is_bot:
            try:
                await bot.ban_chat_member(chat_id, user.id)
                warn = await msg.reply(f"🚫 تم طرد البوت @{user.username or user.first_name} لأن قفل البوتات مفعّل.")
                async def delete_after():
                    await asyncio.sleep(5)
                    try:
                        await warn.delete()
                    except Exception:
                        pass
                asyncio.create_task(delete_after())
            except Exception:
                pass


@bot.on_message(filters.group)
async def handle_group_message(client, msg):
    chat_id = msg.chat.id
    text = msg.text or msg.caption or ""
    clean_text = text.strip()

    # General commands (Help)
    if clean_text.lower() in ["help", "/help", "مساعدة", "/مساعدة"]:
        await msg.reply(HELP_TEXT, disable_web_page_preview=True)
        return

    # Check if sender is an admin
    admin_status = await is_admin(client, msg)

    if admin_status:
        # Admin Commands Handling
        if clean_text in ["الاقفال", "الأقفال", "قائمة الاقفال", "قائمة الأقفال", "الاوامر", "الأوامر"]:
            locks = get_chat_locks(chat_id)
            response = "🛡️ **قائمة إعدادات وأقفال المجموعة:**\n\n"
            for key, ar_name in LOCK_COLUMNS.items():
                status_icon = "🔒 مقفول" if locks.get(key, False) else "🔓 مفتوح"
                response += f"• **{ar_name}**: {status_icon}\n"

            response += "\n━━━━━━━━━━━━━\n"
            response += "⚙️ **للتحكم بالأقفال:**\n"
            response += "• `قفل <النوع>` (مثال: `قفل الصور`)\n"
            response += "• `فتح <النوع>` (مثال: `فتح الصور`)\n"
            response += "• `قفل الكل` / `فتح الكل`"
            await msg.reply(response)
            return

        elif clean_text in ["قفل الكل", "قفل كل شيء"]:
            set_all_chat_locks(chat_id, True)
            await msg.reply("🔒 تم قفل جميع إعدادات وميديا المجموعة بنجاح ✅")
            return

        elif clean_text in ["فتح الكل", "فتح كل شيء"]:
            set_all_chat_locks(chat_id, False)
            await msg.reply("🔓 تم فتح جميع إعدادات وميديا المجموعة بنجاح ✅")
            return

        elif clean_text.startswith("قفل "):
            target_lock = clean_text[4:].strip()
            lock_key = LOCK_ALIASES.get(target_lock)
            if lock_key:
                set_chat_lock(chat_id, lock_key, True)
                lock_name = LOCK_COLUMNS[lock_key]
                await msg.reply(f"🔒 تم قفل **{lock_name}** بنجاح.")
            else:
                await msg.reply(f"❌ لم يتم العثور على قفل باسم `{target_lock}`. أرسل `الاقفال` لمعرفة القائمة.")
            return

        elif clean_text.startswith("فتح "):
            target_lock = clean_text[4:].strip()
            lock_key = LOCK_ALIASES.get(target_lock)
            if lock_key:
                set_chat_lock(chat_id, lock_key, False)
                lock_name = LOCK_COLUMNS[lock_key]
                await msg.reply(f"🔓 تم فتح **{lock_name}** بنجاح.")
            else:
                await msg.reply(f"❌ لم يتم العثور على قفل باسم `{target_lock}`. أرسل `الاقفال` لمعرفة القائمة.")
            return

        # Reply-based Admin Moderation
        if msg.reply_to_message and msg.reply_to_message.from_user:
            target_user = msg.reply_to_message.from_user
            target_user_id = target_user.id
            target_user_name = target_user.first_name
            target_username = f"@{target_user.username}" if target_user.username else target_user_name

            command_parts = clean_text.split()
            command = command_parts[0] if command_parts else ""
            duration = int(command_parts[1]) if len(command_parts) > 1 and command_parts[1].isdigit() else 60
            until_date = datetime.now() + timedelta(minutes=duration)

            if command == "كتم":
                muted_list = get_muted_members(chat_id)
                if target_user_id in muted_list:
                    await msg.reply("العضو مكتوم بالفعل! ❌")
                else:
                    try:
                        await bot.restrict_chat_member(
                            chat_id,
                            target_user_id,
                            ChatPermissions(can_send_messages=False),
                            until_date,
                        )
                        save_muted_member(chat_id, target_user_id, target_user_name, until_date)
                        await msg.reply(
                            f"تم كتم {target_user_name} 🤍 لمدة {duration} دقيقة .\n\n- {target_username}"
                        )
                    except Exception:
                        await msg.reply("لا يمكنني كتم هذا المستخدم لأنه أدمن أو ليس لدي الصلاحيات الكافية.")
                return

            elif command == "طرد":
                banned_list = get_banned_members(chat_id)
                if target_user_id in banned_list:
                    await msg.reply("العضو مطرود بالفعل! ❌")
                else:
                    try:
                        await bot.ban_chat_member(chat_id, target_user_id)
                        save_banned_member(chat_id, target_user_id, target_user_name)
                        await msg.reply(f"تم طرد {target_user_name} 🚪.\n\n- {target_username}")
                    except Exception:
                        await msg.reply("لا يمكنني طرد هذا المستخدم لأنه أدمن أو ليس لدي الصلاحيات الكافية.")
                return

            elif clean_text == "رفع الكتم":
                muted_list = get_muted_members(chat_id)
                if target_user_id not in muted_list:
                    await msg.reply("العضو ليس مكتومًا! ✅")
                else:
                    try:
                        await bot.restrict_chat_member(
                            chat_id,
                            target_user_id,
                            ChatPermissions(can_send_messages=True),
                        )
                        remove_muted_member(chat_id, target_user_id)
                        await msg.reply(f"تم إلغاء الكتم ✅.\n\n- {target_username}")
                    except Exception:
                        await msg.reply("تعذر إلغاء الكتم.")
                return

            elif clean_text == "رفع الحظر":
                banned_list = get_banned_members(chat_id)
                if target_user_id not in banned_list:
                    await msg.reply("العضو ليس محظورًا! ✅")
                else:
                    try:
                        await bot.unban_chat_member(chat_id, target_user_id)
                        remove_banned_member(chat_id, target_user_id)
                        await msg.reply(f"تم إلغاء الحظر 🔄.\n\n- {target_username}")
                    except Exception:
                        await msg.reply("تعذر إلغاء الحظر.")
                return

        # If admin didn't send an admin command, check if they called Nightmare AI
        if text:
            await check_nightmarecall(client, msg, text)
        return

    # Non-Admin Message Handling (Enforce Locks)
    locks = get_chat_locks(chat_id)

    # 1. Chat Lock
    if locks.get("chat"):
        await warn_and_delete(client, msg, "الشات")
        return

    # 2. Photos Lock
    if locks.get("photos") and msg.photo:
        await warn_and_delete(client, msg, "الصور")
        return

    # 3. Videos Lock
    if locks.get("videos") and (msg.video or msg.video_note):
        await warn_and_delete(client, msg, "الفيديو")
        return

    # 4. GIFs Lock
    if locks.get("gifs") and msg.animation:
        await warn_and_delete(client, msg, "المتحركات")
        return

    # 5. Stickers Lock
    if locks.get("stickers") and msg.sticker:
        await warn_and_delete(client, msg, "الستكرات")
        return

    # 6. Voice / Audio Lock
    if locks.get("voice") and (msg.voice or msg.audio):
        await warn_and_delete(client, msg, "الصوت والبصمات")
        return

    # 7. Forwards Lock
    if locks.get("forward") and (
        msg.forward_date
        or msg.forward_from
        or msg.forward_from_chat
        or msg.forward_sender_name
    ):
        await warn_and_delete(client, msg, "التوجيه")
        return

    # 8. Links Lock
    if locks.get("links") and has_link(msg):
        await warn_and_delete(client, msg, "الروابط")
        return

    # 9. Usernames Lock
    if locks.get("usernames") and has_username(msg):
        await warn_and_delete(client, msg, "المعرفات")
        return

    # 10. Tags Lock
    if locks.get("tags") and has_tag(msg):
        await warn_and_delete(client, msg, "التاك")
        return

    # 11. Files Lock
    if locks.get("files") and msg.document and not msg.animation:
        await warn_and_delete(client, msg, "الملفات")
        return

    # 12. Contacts Lock
    if locks.get("contacts") and msg.contact:
        await warn_and_delete(client, msg, "جهات الاتصال")
        return

    # 13. Spam / Long Text Lock (>400 chars)
    if locks.get("spam"):
        text_len = len(msg.text) if msg.text else (len(msg.caption) if msg.caption else 0)
        if text_len > 400:
            await warn_and_delete(client, msg, "الكلايش الطويلة")
            return

    # If message passed locks, check text for bad words & AI calls
    if text:
        isbadword = await check_badwords(client, msg, text)
        if "True" in isbadword:
            try:
                await bot.delete_messages(chat_id, message_ids=msg.id)
            except Exception:
                pass
            try:
                target_user = msg.from_user
                if target_user:
                    until_date = datetime.now() + timedelta(minutes=60)
                    await bot.restrict_chat_member(
                        chat_id,
                        target_user.id,
                        ChatPermissions(can_send_messages=False),
                        until_date,
                    )
                    save_muted_member(chat_id, target_user.id, target_user.first_name, until_date)
                    await bot.send_message(
                        chat_id=chat_id,
                        text="تم حذف رسالة بذيئة وتمَّ كتم العضو وتنبيه المالك 🖤.",
                    )
            except pyrogram.errors.exceptions.bad_request_400.UserAdminInvalid:
                await msg.reply_text("لا يمكنني كتم هذا المستخدم لأنه أدمن أو ليس لدي الصلاحيات الكافية.")
            except Exception:
                pass
            RegBotinfo(msg)
        else:
            await check_nightmarecall(client, msg, text)


if __name__ == "__main__":
    bot.run()
