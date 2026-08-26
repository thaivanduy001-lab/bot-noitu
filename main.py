import discord
import asyncio
import re
import random
import os
import requests
from threading import Thread
from flask import Flask, render_template_string, request, redirect, url_for

# Danh sách cấu hình các kênh (ID kênh & Tên hiển thị)
CHANNELS_CONFIG = {
    1531875015769854054: {"name": "thick-pvp", "active": True},
    1531875015769854054: {"name": "cac", "active": True},
    1531875015769854054: {"name": "bot", "active": True},
    1531875015769854054: {"name": "bot2", "active": True},
    1531875015769854054: {"name": "bot3", "active": True}
}

app = Flask(__name__)

# Giao diện HTML Dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bảng Điều Khiển Nối Từ</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #121212; color: #fff; padding: 20px; display: flex; justify-content: center; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 12px; width: 100%; max-width: 400px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        h2 { text-align: center; color: #5865F2; margin-bottom: 20px; }
        .item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #333; }
        .name { font-weight: bold; font-size: 16px; }
        .switch { position: relative; display: inline-block; width: 50px; height: 26px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #4f545c; transition: .3s; border-radius: 26px; }
        .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: #57F287; }
        input:checked + .slider:before { transform: translateX(24px); }
        .btn { display: block; width: 100%; padding: 12px; margin-top: 20px; background: #5865F2; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Bật/Tắt Kênh Nối Từ</h2>
        <form action="/toggle" method="POST">
            {% for ch_id, info in channels.items() %}
            <div class="item">
                <span class="name"># {{ info.name }}</span>
                <label class="switch">
                    <input type="checkbox" name="{{ ch_id }}" {% if info.active %}checked{% endif %}>
                    <span class="slider"></span>
                </label>
            </div>
            {% endfor %}
            <button type="submit" class="btn">Lưu Cấu Hình</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, channels=CHANNELS_CONFIG)

@app.route('/toggle', methods=['POST'])
def toggle():
    for ch_id in CHANNELS_CONFIG:
        # Kiểm tra xem ID kênh có nằm trong danh sách gửi từ Form lên không
        CHANNELS_CONFIG[ch_id]["active"] = str(ch_id) in request.form
    return redirect(url_for('home'))

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

t = Thread(target=run_web)
t.daemon = True
t.start()

# --- DISCORD SELFBOT LOGIC ---
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
        print(f"Lỗi API: {e}")

    backup_dict = {
        "được": "được việc", "việc": "việc làm", "làm": "làm ăn", "ăn": "ăn uống",
        "mai": "mai sau", "sau": "sau này", "này": "này nọ", "nọ": "nọ kia"
    }
    return backup_dict.get(start_word, f"{start_word} việc")

@client.event
async def on_ready():
    print(f"=== DA DANG NHAP SELFBOT: {client.user} ===")
    asyncio.create_task(send_nt_loop())

async def send_nt_loop():
    await client.wait_until_ready()
    await asyncio.sleep(5)
    
    while not client.is_closed():
        for ch_id, config in CHANNELS_CONFIG.items():
            # Chỉ gửi .nt nếu kênh đó đang BẬT trên Web
            if config["active"]:
                try:
                    channel = client.get_channel(ch_id) or await client.fetch_channel(ch_id)
                    if channel:
                        print(f"[AUTO] Gui .nt vao kenh {config['name']}...")
                        await channel.send(".nt")
                except Exception as e:
                    print(f"Loi gui .nt kenh {config['name']}: {e}")
                await asyncio.sleep(2)
            
        await asyncio.sleep(20)

@client.event
async def on_message(message):
    # Kiểm tra kênh nhắn có tồn tại và đang BẬT hay không
    if message.channel.id not in CHANNELS_CONFIG or not CHANNELS_CONFIG[message.channel.id]["active"]:
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
        print(f"[KENH {CHANNELS_CONFIG[message.channel.id]['name']}] Phat hien: {start_word}")
        await solve_and_reply(message.channel, start_word)

async def solve_and_reply(channel, start_word):
    answer = get_vietnamese_word(start_word)
    if answer:
        print(f"[DAP AN]: {answer}")
        await asyncio.sleep(random.uniform(1.2, 2.5))
        await channel.send(answer)

token = os.getenv('DISCORD_TOKEN') or os.getenv('DISCORD-TOKEN')
client.run(token)
