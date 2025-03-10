import os
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
import requests
import pyrogram
import asyncio
from backgroung import *
from dotenv import load_dotenv
load_dotenv()

os.system("clear")
print("\n- Nightmare: Hi Fenix, I'm Night how can I help you today?\n")

bot = Client("ai",
    api_id=os.getenv("api_id"),
    api_hash=os.getenv("api_hash"),
    bot_token=os.getenv("BOT_TOKEN")
)

muted_members = {}
banned_members = {}

@bot.on_message(filters.command("secret") & filters.private)
async def start(client, message):
    RegBotinfo(message)
    msg = await message.reply("it's E-chan ❤️!")
    i = 0
    while i < 10:
        await msg.edit(f"-How are you shawty?")
        await asyncio.sleep(0.3)
        await msg.edit(f"- How was ur day?🤍..")
        await asyncio.sleep(0.3)
        await msg.edit(f"- Bakayaruu!...")
        await asyncio.sleep(0.3)
        await msg.edit(f"- I miss ya ❤️‍🩹...")
        await asyncio.sleep(0.4)
        await msg.edit(f"- Don't forget that I Wolf u!❤️‍🩹...")
        await asyncio.sleep(0.3)
        await msg.edit(f"- always be good!❤️‍🩹...")
        await asyncio.sleep(0.3)
        await msg.edit(f"- U R My ∞!❤️‍🩹...")
        await asyncio.sleep(0.3)
        await msg.edit(f"- don't be ever be a stranger!🖤...")
        await asyncio.sleep(0.3)
        i += 1

@bot.on_message(filters.command("start") & filters.group)
async def start(client, msg):
    await msg.reply("أهلاً، أنا نايت بوت ذكاء اصطناعي وحماية كروبات، \n\n- `BY: @x1v11x`")

@bot.on_message(filters.command("Arise"))
async def list_muted_and_banned(client, msg):
    response = "قائمة الأعضاء المكتومين والمطرودين:\n\n"
    
    if muted_members:
        response += "📌 الأعضاء المكتومين:\n"
        for user_id, (name, until) in muted_members.items():
            remaining = (until - datetime.now()).total_seconds() if until else "دائم"
            if isinstance(remaining, (int, float)):
                if remaining >= 3600:
                    remaining = f"{remaining // 3600:.0f} ساعة"
                else:
                    remaining = f"{remaining // 60:.0f} دقيقة"
            response += f"- <a href='tg://user?id={user_id}'>{name}</a>: {remaining} متبقية\n"
    else:
        response += "لا يوجد أعضاء مكتومين حاليًا.\n"
    
    response += "\n"
    
    if banned_members:
        response += "🚫 الأعضاء المطرودين:\n"
        for user_id, name in banned_members.items():
            response += f"- <a href='tg://user?id={user_id}'>{name}</a>\n"
    else:
        response += "لا يوجد أعضاء مطرودين حاليًا.\n"
    
    await msg.reply(response, disable_web_page_preview=True)

@bot.on_message(filters.text & filters.group)
async def handle_message(client, msg):
    text = msg.text
    chat_id = msg.chat.id
    target_user = msg.reply_to_message.from_user
    target_user_id = target_user.id if msg.reply_to_message else msg.from_user.id
    target_user_name = target_user.first_name
    until_date = datetime.now() + timedelta(minutes=60)
    
    if await is_admin(client, msg) and msg.reply_to_message:
        command_parts = text.strip().split()
        command = command_parts[0]
        duration = int(command_parts[1]) if len(command_parts) > 1 and command_parts[1].isdigit() else 60
        
        if text == "كتم":
            if target_user_id in muted_members:
                await msg.reply("العضو مكتوم بالفعل! ❌")
            else:
                await bot.restrict_chat_member(chat_id, target_user_id, ChatPermissions(can_send_messages=False), until_date)
                muted_members[target_user_id] = (target_user_name, until_date)
                await msg.reply(f"تم كتم {target_user_name} 🤍 لمدة {duration} دقيقة .\n\n- @{target_user.username}")
        
        elif text == "طرد":
            if target_user_id in banned_members:
                await msg.reply("العضو مطرود بالفعل! ❌")
            else:
                await bot.ban_chat_member(chat_id, target_user_id)
                banned_members[target_user_id] = target_user_name
                await msg.reply(f"تم طرد {target_user_name} 🚪.\n\n- @{target_user.username}")
        
        elif text == "رفع الكتم":
            if target_user_id not in muted_members:
                await msg.reply("العضو ليس مكتومًا! ✅")
            else:
                await bot.restrict_chat_member(chat_id, target_user_id, ChatPermissions(can_send_messages=True))
                muted_members.pop(target_user_id, None)
                await msg.reply(f"تم إلغاء الكتم ✅.\n\n- @{target_user.username}")
        
        elif text == "رفع الطرد":
            if target_user_id not in banned_members:
                await msg.reply("العضو ليس محظوراً! ✅")
            else:
                await bot.unban_chat_member(chat_id, target_user_id)
                banned_members.pop(target_user_id, None)
                await msg.reply(f"تم إلغاء الحظر 🔄.\n\n- @{target_user.username}")
        
        else:
            await check_nightmarecall(client, msg, text)
    
    isbadword = await check_badwords(client, msg, text)
    if "True" in isbadword:
        await bot.delete_messages(chat_id, message_ids=msg.id)
        try:
            if target_user_id not in muted_members:
                await bot.restrict_chat_member(chat_id, target_user_id, ChatPermissions(can_send_messages=False), until_date)
                muted_members[target_user_id] = (target_user_name, until_date)
                await bot.send_message(chat_id=chat_id, text="تم حذف رسالة بذيئة وتمَّ تنبيه المالك 🖤.")
        except pyrogram.errors.exceptions.bad_request_400.UserAdminInvalid:
            await msg.reply_text("لا يمكنني كتم هذا المستخدم لأنه أدمن أو ليس لدي الصلاحيات الكافية.")
        RegBotinfo(msg)
    else:
        await check_nightmarecall(client, msg, text)

bot.run()
