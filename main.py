import discord
import asyncio
import re
import random
import os
import requests
from threading import Thread
from flask import Flask

# Web Server mở cổng cho Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot dang chay 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

t = Thread(target=run_web)
t.start()

CHANNEL_ID = 1497266748087341076 # Hãy chắc chắn ID này đúng 100%
client = discord.Client()

def get_vietnamese_word(start_word):
    start_word = start_word.lower().strip()
    # 1. Tra cứu online qua API
    try:
        url = f"https://vi.wiktionary.org/w/api.php?action=opensearch&search={start_word}&limit=15&format=json"
        res = requests.get(url, timeout=4).json()
        suggestions = res[1]
        for word in suggestions:
            words = word.lower().split()
            if len(words) == 2 and words[0] == start_word:
                return word.lower()
    except Exception as e:
        print(f"Loi tra API: {e}")

    # 2. Bộ từ điển dự phòng phong phú cho các từ phổ biến
    backup_dict = {
        "mai": "mai sau", "sau": "sau này", "này": "này nọ", "nọ": "nọ kia",
        "hoa": "hoa hồng", "hồng": "hồng hộc", "hộc": "hộc máu", "máu": "máu me",
        "yêu": "yêu thương", "thương": "thương hại", "hại": "hại điện", "điện": "điện thoại",
        "thoại": "thoại mái", "mái": "mái nhà", "nhà": "nhà cửa", "cửa": "cửa sổ",
        "sổ": "sổ sách", "sách": "sách vở", "vở": "vở kịch", "kịch": "kịch bản",
        "bản": "bản đồ", "đồ": "đồ đạc", "đạc": "đạc điền", "điền": "điền dã"
    }
    return backup_dict.get(start_word, f"{start_word} tinh")

@client.event
async def on_ready():
    print(f"=== ĐÃ ĐĂNG NHẬP: {client.user} ===")
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
            print("[TỰ ĐỘNG] Dang gui .nt...")
            await channel.send(".nt")
        except Exception as e:
            print(f"Loi gui .nt: {e}")
        await asyncio.sleep(60)

@client.event
async def on_message(message):
    if message.channel.id != CHANNEL_ID:
        return

    # Không tự trả lời tin nhắn của chính mình
    if message.author.id == client.user.id:
        return

    # Lấy toàn bộ văn bản từ tin nhắn hoặc Embed
    full_text = message.content or ""
    if message.embeds:
        for embed in message.embeds:
            full_text += " " + (embed.description or "")
            full_text += " " + " ".join([f"{f.name} {f.value}" for f in embed.fields])

    # Bắt tất cả các dạng từ từ Bot game (bất kể dùng hoa/thường)
    match = re.search(r"(?:bắt đầu bằng|bắt đầu bằng tiếng|tiếp theo|từ):\s*([^\s\|]+)", full_text, re.IGNORECASE)
    if match:
        start_word = match.group(1).strip()
        print(f"[PHÁT HIỆN ĐỀ]: Tiếng bắt đầu = '{start_word}'")
        await solve_and_reply(message.channel, start_word)

async def solve_and_reply(channel, start_word):
    answer = get_vietnamese_word(start_word)
    if answer:
        print(f"[ĐÃ TÌM TỪ]: Tra lời -> '{answer}'")
        await asyncio.sleep(random.uniform(1.5, 3.0)) # Giả lập thời gian gõ của người thật
        await channel.send(answer)

client.run(os.getenv('DISCORD-TOKEN'))
