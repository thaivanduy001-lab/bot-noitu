import discord
import asyncio
import re
import random
import os
import requests
from threading import Thread
from flask import Flask

# 1. Tạo Web Server giả lập để UptimeRobot giữ Render chạy 24/7
app = Flask(__name__)

@app.route('/')
def home():
    return "Selfbot dang chay 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

t = Thread(target=run_web)
t.start()

# 2. Danh sách ID kênh chạy nối từ
CHANNEL_IDS = [
    1497266748087341076, 
    1485274014308892831, 
    1540945642686255104, 
    1540971960958451832, 
    1540972002628870215
]

# Khởi tạo Selfbot Client
client = discord.Client()

# Hàm tra cứu từ điển Wiktionary + Backup
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
    print(f"==========================================")
    print(f"=== DA DANG NHAP SELFBOT: {client.user} ===")
    print(f"==========================================")
    asyncio.create_task(send_nt_loop())

# Vòng lặp gửi lệnh .nt tự động
async def send_nt_loop():
    await client.wait_until_ready()
    await asyncio.sleep(5)  # Chờ 5s cho tài khoản load xong bộ nhớ Cache
    
    while not client.is_closed():
        for ch_id in CHANNEL_IDS:
            try:
                # Tìm kênh trong Cache hoặc Fetch trực tiếp từ API
                channel = client.get_channel(ch_id)
                if not channel:
                    channel = await client.fetch_channel(ch_id)
                
                if channel:
                    print(f"[AUTO] Dang gui .nt vao kenh: {ch_id}")
                    await channel.send(".nt")
                else:
                    print(f"[LOI] Khong tim thay kenh ID: {ch_id}")
            except Exception as e:
                print(f"[LOI GUI .NT - Kenh {ch_id}]: {e}")
            
            # Tạm nghỉ 2s giữa các kênh để tránh dính Spam/Rate limit
            await asyncio.sleep(2)
            
        # Nghỉ 18 giây trước lượt gửi tiếp theo
        await asyncio.sleep(18)

# Lắng nghe và tự động giải bài nối từ
@client.event
async def on_message(message):
    if message.channel.id not in CHANNEL_IDS:
        return

    # Bỏ qua tin nhắn do chính mình gửi
    if message.author.id == client.user.id:
        return

    full_text = message.content or ""
    
    # Đọc tin nhắn dạng Embed (Bot Game thường gửi dạng Embed)
    if message.embeds:
        for embed in message.embeds:
            full_text += " " + (embed.description or "")
            if embed.footer and embed.footer.text:
                full_text += " " + embed.footer.text
            full_text += " " + " ".join([f"{f.name} {f.value}" for f in embed.fields])

    match = re.search(r"bắt đầu bằng:\s*([^\s\|]+)", full_text, re.IGNORECASE)
    if match:
        start_word = match.group(1).strip()
        print(f"[PHAT HIEN TU - Kenh {message.channel.id}]: {start_word}")
        await solve_and_reply(message.channel, start_word)

async def solve_and_reply(channel, start_word):
    answer = get_vietnamese_word(start_word)
    if answer:
        print(f"[TRA LOI]: {answer}")
        await asyncio.sleep(random.uniform(1.2, 2.5))  # Giả lập thời gian gõ của người thật
        await channel.send(answer)

# Lấy Token từ Environment Variable của Render
token = os.getenv('DISCORD_TOKEN') or os.getenv('DISCORD-TOKEN')
client.run(token)
