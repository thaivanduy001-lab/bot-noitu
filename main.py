import discord
import asyncio
import re
import random
import os
import requests
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot dang chay 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

t = Thread(target=run_web)
t.start()

# Danh sách 3 kênh bạn muốn chạy
CHANNEL_IDS = [1497266748087341076, 1485274014308892831, 1540945642686255104]
client = discord.Client()

def get_vietnamese_word(start_word):
    start_word = start_word.lower().strip()
    try:
        url = f"https://vi.wiktionary.org/w/api.php?action=opensearch&search={start_word}&limit=20&format=json"
        res = requests.get(url, timeout=4).json()
        suggestions = res[1]
        for word in suggestions:
            words = word.lower().split()
            if len(words) == 2 and words[0] == start_word:
                return word.lower()
    except Exception as e:
        print(f"Loi tra API: {e}")

    backup_dict = {
        "được": "được việc", "việc": "việc làm", "làm": "làm ăn", "ăn": "ăn uống",
        "mai": "mai sau", "sau": "sau này", "này": "này nọ", "nọ": "nọ kia",
        "hoa": "hoa hồng", "hồng": "hồng hộc", "hộc": "hộc máu", "máu": "máu me"
    }
    return backup_dict.get(start_word, f"{start_word} việc")

@client.event
async def on_ready():
    print(f"=== ĐÃ ĐĂNG NHẬP: {client.user} ===")
    client.loop.create_task(send_nt_loop())

async def send_nt_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        for ch_id in CHANNEL_IDS:
            try:
                channel = client.get_channel(ch_id) or await client.fetch_channel(ch_id)
                if channel:
                    print(f"[AUTO] Gui .nt vao kenh {ch_id}...")
                    await channel.send(".nt")
            except Exception as e:
                print(f"Loi gui .nt kenh {ch_id}: {e}")
        await asyncio.sleep(25)

@client.event
async def on_message(message):
    # Kiểm tra xem tin nhắn có thuộc 1 trong 3 kênh không
    if message.channel.id not in CHANNEL_IDS:
        return

    if message.author.id == client.user.id:
        return

    full_text = message.content or ""
    
    if message.embeds:
        for embed in message.embeds:
            full_text += " " + (embed.description or "")
            if embed.footer and embed.footer.text:
                full_text += " " + embed.footer.text
            full_text += " " + " ".join([f"{f.name} {f.value}" for f in embed.fields])

    match = re.search(r"bắt đầu bằng:\s*([^\s\|]+)", full_text, re.IGNORECASE)
    if match:
        start_word = match.group(1).strip()
        print(f"[KENH {message.channel.id}] Phat hien tu: {start_word}")
        await solve_and_reply(message.channel, start_word)

async def solve_and_reply(channel, start_word):
    answer = get_vietnamese_word(start_word)
    if answer:
        print(f"[DAP AN]: {answer}")
        await asyncio.sleep(random.uniform(1.2, 2.5))
        await channel.send(answer)

client.run(os.getenv('DISCORD_TOKEN'))
