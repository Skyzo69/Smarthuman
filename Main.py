import requests
import asyncio
import random

# Minta input dari user
try:
    TARGET_CHANNEL_ID = int(input("Masukkan ID channel: ").strip())
    MIN_INTERVAL = float(input("Set Interval Waktu Minimal Antar Pesan (detik, min 1.0): ").strip())
    MAX_INTERVAL = float(input("Set Interval Waktu Maksimal Antar Pesan (detik): ").strip())

    if MIN_INTERVAL < 1.0 or MAX_INTERVAL < MIN_INTERVAL:
        print("❌ Input tidak valid! Pastikan MIN_INTERVAL ≥ 1.0 dan MAX_INTERVAL ≥ MIN_INTERVAL.")
        exit(1)

    # Minta user buat custom prompt
    SYSTEM_PROMPT = input("Masukkan prompt AI: ").strip()

except ValueError:
    print("❌ Input tidak valid! Pastikan memasukkan angka.")
    exit(1)

# Load token user + API Key dari file token.txt
user_tokens = []
api_keys = {}

try:
    with open("token.txt", "r") as f:
        for line in f.readlines():
            parts = line.strip().split("|")
            if len(parts) == 2:
                token, api_key = parts
                user_tokens.append(token)
                api_keys[token] = api_key
            else:
                print(f"❌ Format salah di line: {line}")
except FileNotFoundError:
    print("❌ File token.txt tidak ditemukan!")
    exit(1)

if len(user_tokens) < 2:
    print("❌ Minimal butuh 2 token buat percakapan.")
    exit(1)

TOKEN_1 = user_tokens[0]
TOKEN_2 = user_tokens[1]

# Class ChatBot pakai requests
class ChatBot:
    def __init__(self, token, api_key):
        self.token = token
        self.api_key = api_key
        self.last_message_id = None  
        self.chat_history = []  

    def send_request(self, method, endpoint, json_data=None):
        """Helper buat kirim request ke Discord API"""
        url = f"https://discord.com/api/v9/{endpoint}"
        headers = {"Authorization": self.token, "Content-Type": "application/json"}
        
        response = requests.request(method, url, headers=headers, json=json_data)
        if response.status_code not in [200, 201, 204]:
            print(f"❌ Error Discord API: {response.status_code} - {response.text}")
            return None
        return response.json() if response.text else None

    def send_message(self, content, reply_to=None):
        """Kirim pesan ke channel"""
        data = {"content": content}
        if reply_to:
            data["message_reference"] = {"message_id": reply_to}

        response = self.send_request("POST", f"channels/{TARGET_CHANNEL_ID}/messages", json_data=data)
        if response:
            self.last_message_id = response.get("id")
            self.chat_history.append({"role": "assistant", "content": content})  
            if len(self.chat_history) > 5:
                self.chat_history.pop(0)  
            return self.last_message_id
        return None

    def get_ai_response(self, user_message):
        """Dapatkan balasan AI dari OpenAI API"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for chat in self.chat_history[-5:]:
            messages.append({"role": chat["role"], "content": chat["content"]})

        messages.append({"role": "user", "content": user_message})

        data = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": 0.8
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                ai_reply = response.json()["choices"][0]["message"]["content"]
                self.chat_history.append({"role": "assistant", "content": ai_reply})
                return ai_reply
            else:
                print(f"❌ Error OpenAI API: {response.status_code} - {response.text}")
                return f"Oops, error with AI response! ({response.status_code})"
        except Exception as e:
            print(f"❌ Error OpenAI: {e}")
            return "Oops, error with AI response!"

# Inisialisasi bot
bot1 = ChatBot(TOKEN_1, api_keys[TOKEN_1])
bot2 = ChatBot(TOKEN_2, api_keys[TOKEN_2])

async def start_chat():
    """Loop percakapan antar bot"""
    
    first_message = random.choice(["Hey, what's up", "Yo! How's ur day", "Ayo, wassup"])
    bot1.last_message_id = bot1.send_message(first_message)
    bot1.chat_history.append({"role": "user", "content": first_message})  
    print(f"💬 Bot 1: {first_message}")

    await asyncio.sleep(random.uniform(MIN_INTERVAL, MAX_INTERVAL))

    last_response = first_message

    while True:
        if bot1.last_message_id:
            bot2_reply = bot2.get_ai_response(last_response)  
            bot2.last_message_id = bot2.send_message(bot2_reply, reply_to=bot1.last_message_id)
            print(f"💬 Bot 2: {bot2_reply}")
            last_response = bot2_reply  

        await asyncio.sleep(random.uniform(MIN_INTERVAL, MAX_INTERVAL))

        if bot2.last_message_id:
            bot1_reply = bot1.get_ai_response(last_response)  
            bot1.last_message_id = bot1.send_message(bot1_reply, reply_to=bot2.last_message_id)
            print(f"💬 Bot 1: {bot1_reply}")
            last_response = bot1_reply  

        await asyncio.sleep(random.uniform(MIN_INTERVAL, MAX_INTERVAL))

if __name__ == "__main__":
    try:
        asyncio.run(start_chat())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_chat())
