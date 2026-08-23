import discord
import asyncio
import re
import random
import os
import requests
from threading import Thread
from flask import Flask

# 1. Khởi tạo Web Server để mở cổng Port cho Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot dang chay 24/7!"

def run_web():
    # Render sẽ tự cấp cổng PORT, nếu không có sẽ dùng cổng 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Tách luồng chạy Web Server ngầm
t = Thread(target=run_web)
t.start()

# 2. Cấu hình Bot Discord
CHANNEL_ID = 1485274014308892831
client = discord.Client()

def get_vietnamese_word(start_word):
    try:
        url = f"https://vi.wiktionary.org/w/api.php?action=opensearch&search={start_word}&limit=10&format=json"
        res = requests.get(url, timeout=5).json()
        suggestions = res[1]
        for word in suggestions:
            words = word.lower().split()
            if len(words) == 2 and words[0] == start_word.lower():
                return word.lower()
    except Exception as e:
        print(f"Loi tra tu dien: {e}")
    
    backup_dict = {
        "mai": "mai sau",
        "sau": "sau này",
        "này": "này nọ"
    }
    return backup_dict.get(start_word.lower(), None)

@client.event
async def on_ready():
    print(f"Da dang nhap thanh cong: {client.user}")
    client.loop.create_task(send_nt_loop())

async def send_nt_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        try:
            channel = await client.fetch_channel(CHANNEL_ID)
        except Exception:
            return

    while not client.is_closed():
        try:
            print("Dang tu dong gui lenh .nt ...")
            await channel.send(".nt")
        except Exception as e:
            print(f"Loi gui tin nhan: {e}")
        await asyncio.sleep(60)

@client.event
async def on_message(message):
    if message.channel.id != CHANNEL_ID:
        return

    if message.embeds:
        for embed in message.embeds:
            full_text = (embed.description or "") + " " + "".join([f"{f.name} {f.value}" for f in embed.fields])
            match = re.search(r"bắt đầu bằng:\s*([^\s\|]+)", full_text, re.IGNORECASE)
            if match:
                await solve_and_reply(message.channel, match.group(1).strip())
                return

    content = message.content or ""
    if "Tiếp theo phải bắt đầu bằng tiếng:" in content or "bắt đầu bằng tiếng:" in content:
        match = re.search(r"bắt đầu bằng tiếng:\s*([^\s\|]+)", content, re.IGNORECASE)
        if match:
            await solve_and_reply(message.channel, match.group(1).strip())

async def solve_and_reply(channel, start_word):
    answer = get_vietnamese_word(start_word)
    if answer:
        await asyncio.sleep(random.uniform(1.5, 3.5))
        await channel.send(answer)

client.run(os.getenv('DISCORD-TOKEN'))
