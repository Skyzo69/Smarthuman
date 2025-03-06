import discord
import openai
import asyncio
import random
import os

# Minta input dari user untuk channel ID dan interval waktu antar pesan
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

# Load token bot + API Key dari file token.txt
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

# Kelas bot Discord
class ChatBot(discord.Client):
    def __init__(self, token, all_bots):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True  # Wajib biar bisa baca pesan
        super().__init__(intents=intents)

        self.token = token
        self.api_key = api_keys[token]  # Ambil API Key sesuai bot ini
        self.all_bots = all_bots
        self.channel = None  # Simpan channel
        self.chat_history = []  # Simpan history chat per bot
        self.last_message_ids = {}  # Simpan ID pesan per bot untuk reply

    async def on_ready(self):
        print(f"✅ {self.user} has connected.")

        # Fetch channel setelah bot ready
        try:
            self.channel = await self.fetch_channel(TARGET_CHANNEL_ID)
            if self.channel is None:
                print(f"⚠️ Channel ID {TARGET_CHANNEL_ID} tidak ditemukan!")
                return
        except discord.NotFound:
            print(f"❌ Error: Channel ID {TARGET_CHANNEL_ID} tidak ditemukan!")
            return
        except discord.Forbidden:
            print(f"❌ Error: Bot tidak punya izin melihat channel ini!")
            return
        except Exception as e:
            print(f"❌ Error lain: {e}")
            return
        
        await self.start_conversation()

    async def get_ai_response(self, user_message):
        """Gunakan API Key bot ini untuk dapat balasan dari OpenAI"""
        openai.api_key = self.api_key  # Gunakan API Key sesuai bot ini

        messages = [{"role": "system", "content": "You are a fun, informal chatbot in an online chatroom. Don't say you're an AI."}]
        
        # Tambahkan history chat bot ini
        for chat in self.chat_history[-5:]:
            messages.append({"role": chat["role"], "content": chat["content"]})

        messages.append({"role": "user", "content": user_message})

        # Kirim permintaan ke OpenAI
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.7
            )

            ai_reply = response["choices"][0]["message"]["content"]
            self.chat_history.append({"role": "assistant", "content": ai_reply})

            return ai_reply
        except Exception as e:
            print(f"❌ Error OpenAI: {e}")
            return "Oops, error with AI response!"

    async def start_conversation(self):
        """Loop percakapan antar bot"""
        last_messages = {}

        while True:
            sender_bot = random.choice(self.all_bots)  
            receiver_bot = random.choice([b for b in self.all_bots if b != sender_bot])  

            user_message = last_messages.get(sender_bot, "Hey, what's up?")
            ai_response = await self.get_ai_response(user_message)
            last_messages[receiver_bot] = ai_response  

            if self.channel:
                try:
                    last_msg_id = self.last_message_ids.get(receiver_bot)  # Ambil ID pesan terakhir
                    if last_msg_id:
                        last_msg = await self.channel.fetch_message(last_msg_id)
                        sent_message = await last_msg.reply(ai_response)  # Reply ke pesan sebelumnya
                    else:
                        sent_message = await self.channel.send(ai_response)  # Kirim biasa kalau belum ada ID

                    self.last_message_ids[sender_bot] = sent_message.id  # Simpan ID pesan terbaru
                    print(f"💬 {self.user} -> {ai_response}")  # Logging pesan di terminal

                except discord.NotFound:
                    print("⚠️ Pesan terakhir tidak ditemukan, mengirim biasa.")
                    sent_message = await self.channel.send(ai_response)
                    self.last_message_ids[sender_bot] = sent_message.id
                except discord.Forbidden:
                    print("❌ Bot tidak punya izin mengirim pesan di channel ini!")
                    return
                except Exception as e:
                    print(f"❌ Error saat mengirim pesan: {e}")
                    return
        
            wait_time = random.uniform(MIN_INTERVAL, MAX_INTERVAL)  # Tunggu sesuai rentang waktu
            print(f"⏳ Menunggu {wait_time:.2f} detik sebelum pesan berikutnya...")
            await asyncio.sleep(wait_time)

# Fungsi untuk menjalankan beberapa bot sekaligus
async def start_bots():
    bots = []
    for token in user_tokens:
        bot = ChatBot(token, user_tokens)
        bots.append(bot)
    
    await asyncio.gather(*(bot.start(token) for bot in bots))  # Jalankan semua bot bersamaan

# Jalankan semua bot
if __name__ == "__main__":
    asyncio.run(start_bots())
