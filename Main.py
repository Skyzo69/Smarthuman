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

if not user_tokens:
    print("❌ Tidak ada token yang dimuat! Pastikan file token.txt benar.")
    exit(1)

# Class ChatBot pakai requests
class ChatBot:
    def __init__(self, token, all_bots):
        self.token = token
        self.api_key = api_keys[token]
        self.all_bots = all_bots
        self.last_message_ids = {}  # Simpan ID pesan terakhir per channel
        self.chat_history = []  # Simpan history chat

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
            return response.get("id")
        return None

    def get_ai_response(self, user_message):
        """Dapatkan balasan dari OpenAI"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "system", "content": "Oke sekarang jadi lah ai yang friendly menggunakan bahasa Inggris informal/sehari hari dan jangan ngaku kalau kamu ai ketika di tanya. Tambahkan emote seperlunya! Jangan banyak tanya, seperlunya aja! Jadi lah seperti manusia."}]
        for chat in self.chat_history[-5:]:
            messages.append({"role": chat["role"], "content": chat["content"]})

        messages.append({"role": "user", "content": user_message})

        data = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": 0.7
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

    async def start_conversation(self):
        """Loop percakapan antar bot"""
        last_messages = {}

        while True:
            if len(self.all_bots) < 2:
                print("❌ Tidak cukup bot untuk percakapan! Minimal 2 bot diperlukan.")
                return

            sender_bot, receiver_bot = random.sample(self.all_bots, 2)

            user_message = last_messages.get(sender_bot, "Hey, what's up?")
            ai_response = self.get_ai_response(user_message)
            last_messages[receiver_bot] = ai_response

            # Kirim pesan
            last_msg_id = self.last_message_ids.get(receiver_bot)
            sent_message_id = self.send_message(ai_response, reply_to=last_msg_id)
            if sent_message_id:
                self.last_message_ids[sender_bot] = sent_message_id
                print(f"💬 {self.token[:10]}... -> {ai_response}")  # Logging pesan

            wait_time = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
            print(f"⏳ Menunggu {wait_time:.2f} detik sebelum pesan berikutnya...")
            await asyncio.sleep(wait_time)

# Jalankan semua bot
async def start_bots():
    if len(user_tokens) < 2:
        print("❌ Tidak cukup bot! Minimal 2 bot diperlukan untuk percakapan.")
        return

    bots = [ChatBot(token, user_tokens) for token in user_tokens]
    
    # Pakai `asyncio.create_task()` biar nggak nunggu satu per satu
    tasks = [asyncio.create_task(bot.start_conversation()) for bot in bots]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(start_bots())
    except RuntimeError:  
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_bots())
