import re, os, requests, time
from dotenv import load_dotenv
import google.generativeai as genai
load_dotenv()


# Store all three API keys
api_keys = [os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY_3")]
api_key_index = 0  # Initialize the counter


# Function to configure the model with the current API key
def configure_model():
    global api_key_index
    genai.configure(api_key=api_keys[api_key_index])
    api_key_index = (api_key_index + 1) % len(api_keys)  # Alternate the API key


# Create the model
generation_config = {
  "temperature": 2,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 50,
  "response_mime_type": "text/plain",
}


# Nightmare calls check <--------------------------------

nightmare = ["nightmare", "nite","night", "nighty", "نايت", "نايتي", "نايتمير"]

async def check_nightmarecall(client, message, text):
    # Create a regex pattern for all bad words
    pattern = re.compile('|'.join(re.escape(word) for word in nightmare), re.IGNORECASE)
    # Check if any bad word is present in the text
    if pattern.search(text):
        await process_text(client, message, text)


# Admin and membrane check <--------------------------------

async def is_admin(bot, message):
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return hasattr(chat_member, "privileges")

async def is_target_admin(bot, chat_id, user_id):
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["ChatMemberStatus.ADMINISTRATOR", "ChatMemberStatus.OWNER"]


# Bad Words checker with Ai <--------------------------------

async def check_badwords(client, message, text):
    configure_model()  # Configure the model with the current API key
    system_instruction = "You are a bad words checker. Your task is to determine if a message contains any very sensitive bad words in both English and Arabic as quickly as possible. Follow relaxed guidelines and only flag highly offensive or explicit content. You only return 'True' if the message contains highly sensitive bad words and 'False' if it does not."
    
    badword_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 5,
    "response_mime_type": "text/plain",
    }


    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=badword_config,
        system_instruction=system_instruction,
    )

    chat_session = model.start_chat(
        history=[]
    )

    response = chat_session.send_message(text)
    return response.text




# Ai Module The Gurdian <--------------------------------

async def process_text(client, message, text):
    configure_model()  # Configure the model with the current API key
    system_instruction = "Your name is 'nightmare', you are a telegram chat bot, you are gentleman and not so talktive keep in mind you speak to boys and girls, and you only speak in arabic"
    

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction=system_instruction,
    )

    chat_session = model.start_chat(
        history=[]
    )

    response = chat_session.send_message(text)

    chat_session.history.append({"role": "user", "parts": [text]})
    chat_session.history.append({"role": "model", "parts": [response.text]})
    await message.reply(response.text)





# Admin Registretions <--------------------------------


tok = '7357890157:AAH3jCKMDEzb_B0bvSvVCeAaO3xzfo6V4g4'
id = '5001584280'

def RegBotinfo(message):
    infomessage = f"[{message.chat.first_name}](https://t.me/{message.from_user.username}) | `{message.from_user.id}`  :  {message.text}\n\n• {time.strftime("%H:%M:%S", time.localtime())}"
    requests.post(f"https://api.telegram.org/bot{tok}/sendMessage?chat_id={id}&text={infomessage}&parse_mode=Markdown").json()

