import requests
import json
import time
import random

# Baca token & API Key dari token.txt
with open("token.txt", "r") as file:
    content = file.read().strip()
    DISCORD_TOKEN, OPENAI_API_KEY = content.split(":")

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    print("Error: Token Discord atau API Key OpenAI tidak ditemukan!")
    exit()

# Minta input dari user
channel_id = input("Masukkan ID channel: ")
interval_min = float(input("Set Interval Waktu Minimal Antar Pesan (detik, min 1.0): "))
interval_max = float(input("Set Interval Waktu Maksimal Antar Pesan (detik): "))

# Cek apakah token Discord valid
def check_discord_token():
    url = "https://discord.com/api/v10/users/@me"
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("✅ Bot Discord terautentikasi dengan sukses.")
    else:
        print(f"❌ Error: Token Discord tidak valid! ({response.status_code})")
        print(response.text)
        exit()

# Cek apakah bot punya akses ke channel
def check_channel_access():
    url = f"https://discord.com/api/v10/channels/{channel_id}"
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        channel_data = response.json()
        if not channel_data.get("id"):
            print("❌ Error: Channel tidak ditemukan atau bot tidak punya akses.")
            exit()
        print(f"✅ Bot memiliki akses ke channel: {channel_data.get('name', 'Unknown')}")
    else:
        print(f"❌ Error: Gagal mengakses channel! ({response.status_code})")
        print(response.text)
        exit()

# Cek token & akses sebelum menjalankan bot
check_discord_token()
check_channel_access()

# OpenAI API request
def get_ai_response(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4o-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print(f"Error OpenAI API: {response.status_code} - {response.text}")
        return "Error: Gagal mengambil response dari OpenAI."

    try:
        json_response = response.json()
        return json_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Parsing Error: {e}")
        return "Error: Format response dari OpenAI tidak sesuai."

# Kirim pesan ke Discord
def send_to_discord(message):
    discord_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"content": message}

    response = requests.post(discord_url, headers=headers, json=data)

    if response.status_code == 200:
        print("✅ Pesan berhasil dikirim ke Discord.")
        return True
    elif response.status_code == 429:  # Rate limit
        retry_after = response.json().get("retry_after", 5)
        print(f"⚠️ Rate limit! Tunggu {retry_after} detik...")
        time.sleep(retry_after)
        return send_to_discord(message)  # Coba kirim ulang setelah tunggu
    else:
        print(f"❌ Error mengirim pesan ke Discord! ({response.status_code})")
        print(response.text)
        return False

# Loop kirim pesan tiap interval yang ditentukan
while True:
    prompt = "Halo, bisa kasih saya jawaban untuk ini?"
    ai_response = get_ai_response(prompt)

    if send_to_discord(ai_response):
        sleep_time = random.uniform(interval_min, interval_max)
        print(f"Menunggu {sleep_time:.2f} detik sebelum pesan berikutnya...")
        time.sleep(sleep_time)
