import discord
import asyncio
import os
from threading import Thread
from flask import Flask, render_template_string, request, jsonify

# ==========================================
# CẤU HÌNH CƠ BẢN (ĐÃ CẤU HÌNH ID CỦA BẠN)
# ==========================================
DEFAULT_VOICE_ID = 1417884212249493638        # ID Kênh Voice (SHADOW GLADE - Chung)
CHAT_DONATE_CHANNEL_ID = 1531875015769854054  # ID Kênh chat để gõ lệnh .donate
MAIN_ACC_ID = 1326098743170170932              # ID Discord Acc chính nhận tiền

# Nạp thư viện Opus hỗ trợ Voice trên Linux (Render)
try:
    discord.opus.load_opus('libopus.so.0')
except Exception:
    try:
        discord.opus.load_opus('libopus.so')
    except Exception:
        pass

# Bộ nhớ lưu trữ dữ liệu các Account
ACCOUNTS_DATA = {} # Format: {token: {"name": str, "voice_enabled": bool, "status": str, "bot_obj": client}}

app = Flask(__name__)

# Giao diện Dashboard Quản Lý
HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Voice Multi-Account Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #fff; margin: 0; padding: 15px; }
        h2 { color: #5865F2; text-align: center; margin-bottom: 20px; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        textarea { width: 100%; padding: 12px; background: #2b2b2b; color: #fff; border: 1px solid #444; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { background: #5865F2; color: #fff; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; font-size: 15px; margin-top: 10px; }
        button:hover { background: #4752C4; }
        .acc-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #2d2d2d; }
        .acc-row:last-child { border-bottom: none; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-online { background: #2ed573; color: #000; }
        .badge-offline { background: #ff4757; color: #fff; }
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #444; transition: .4s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: #2ed573; }
        input:checked + .slider:before { transform: translateX(20px); }
    </style>
</head>
<body>
    <h2>🎙️ DISCORD VOICE & AUTO DONATE PANEL</h2>
    
    <div class="card">
        <h3>Thêm / Cập nhật Token</h3>
        <form action="/add_tokens" method="POST">
            <p><small style="color: #bbb;">Nhập mỗi Token trên 1 dòng (Định dạng: <code>Token|TênGợiNhớ</code>).</small></p>
            <textarea name="token_list" rows="5" placeholder="Token1|Acc1&#10;Token2|Acc2"></textarea>
            <button type="submit">Lưu & Khởi Chạy Ngay</button>
        </form>
    </div>

    <div class="card">
        <h3>Danh Sách Account Đang Treo (Tổng: {{ accounts|length }})</h3>
        {% if not accounts %}
            <p style="color: #888; text-align: center;">Chưa có Account nào được thêm.</p>
        {% endif %}
        {% for token, acc in accounts.items() %}
        <div class="acc-row">
            <div>
                <strong>{{ acc.name }}</strong> 
                <span class="badge {{ 'badge-online' if acc.status == 'Online' else 'badge-offline' }}">{{ acc.status }}</span>
                <br><small style="color: #888;">Token: {{ token[:14] }}...</small>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 13px; color: #aaa;">Voice:</span>
                <label class="switch">
                    <input type="checkbox" onchange="toggleVoice('{{ token }}', this.checked)" {{ 'checked' if acc.voice_enabled else '' }}>
                    <span class="slider"></span>
                </label>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        function toggleVoice(token, enabled) {
            fetch('/toggle_voice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, enabled: enabled })
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_DASHBOARD, accounts=ACCOUNTS_DATA)

@app.route('/add_tokens', methods=['POST'])
def add_tokens():
    raw_text = request.form.get('token_list', '')
    lines = raw_text.strip().split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        parts = line.strip().split('|')
        token = parts[0].strip()
        custom_name = parts[1].strip() if len(parts) > 1 else "Discord Acc"

        if token not in ACCOUNTS_DATA or ACCOUNTS_DATA[token]['status'] != 'Online':
            ACCOUNTS_DATA[token] = {
                "name": custom_name,
                "voice_enabled": True,
                "status": "Starting...",
                "bot_obj": None
            }
            asyncio.run_coroutine_threadsafe(start_new_account(token, custom_name), bot_loop)

    return "<script>alert('Đã thêm Token!'); window.location.href='/';</script>"

@app.route('/toggle_voice', methods=['POST'])
def toggle_voice():
    data = request.json
    token = data.get('token')
    enabled = data.get('enabled')
    if token in ACCOUNTS_DATA:
        ACCOUNTS_DATA[token]['voice_enabled'] = enabled
        bot = ACCOUNTS_DATA[token]['bot_obj']
        if bot:
            if enabled:
                asyncio.run_coroutine_threadsafe(bot.join_voice(), bot_loop)
            else:
                asyncio.run_coroutine_threadsafe(bot.leave_voice(), bot_loop)
    return jsonify({"status": "ok"})

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# ==========================================
# CLASS BOT TREO VOICE & BẢO VỆ KẾT NỐI
# ==========================================
class VoiceSelfBot(discord.Client):
    def __init__(self, token, custom_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_token = token
        self.custom_name = custom_name
        self.donate_task = None
        self.keep_alive_task = None

    async def on_ready(self):
        real_name = f"{self.user.name}"
        if self.custom_name == "Discord Acc":
            self.custom_name = real_name
        
        ACCOUNTS_DATA[self.user_token]['name'] = self.custom_name
        ACCOUNTS_DATA[self.user_token]['status'] = "Online"
        ACCOUNTS_DATA[self.user_token]['bot_obj'] = self

        print(f"🟢 [ONLINE] {self.custom_name} ({self.user})")

        # Chờ 3s cho Gateway ổn định rồi nhảy vào Voice
        await asyncio.sleep(3)
        if ACCOUNTS_DATA[self.user_token]['voice_enabled']:
            await self.join_voice()

        # Kích hoạtAuto Donate mỗi 1 giờ cho các tài khoản Clone
        if str(self.user.id) != str(MAIN_ACC_ID) and not self.donate_task:
            self.donate_task = asyncio.create_task(self.hourly_donate_loop())

        # Kích hoạt vòng lặp kiểm tra trạng thái Voice định kỳ (Mỗi 60 giây)
        if not self.keep_alive_task:
            self.keep_alive_task = asyncio.create_task(self.keep_voice_alive_loop())

    async def join_voice(self):
        try:
            channel = self.get_channel(DEFAULT_VOICE_ID) or await self.fetch_channel(DEFAULT_VOICE_ID)
            if channel:
                # Gửi Gateway WebSocket State trực tiếp (Mute & Deaf để tiết kiệm tài nguyên)
                await self.ws.voice_state(channel.guild.id, channel.id, self_mute=True, self_deaf=True)
                print(f"🔊 [{self.custom_name}] Đã vào Kênh Voice {DEFAULT_VOICE_ID}")
        except Exception as e:
            print(f"❌ [{self.custom_name}] Lỗi vào Voice: {e}")

    async def leave_voice(self):
        try:
            channel = self.get_channel(DEFAULT_VOICE_ID)
            if channel:
                await self.ws.voice_state(channel.guild.id, None)
                print(f"🔇 [{self.custom_name}] Đã rời Kênh Voice")
        except Exception as e:
            print(f"❌ [{self.custom_name}] Lỗi rời Voice: {e}")

    # XỬ LÝ SỰ KIỆN KHI BỊ KICK / MOVE RA KHỎI VOICE
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.user.id:
            # Bị thoát hoặc bị kick ra khỏi Kênh
            if before.channel and after.channel is None:
                if ACCOUNTS_DATA.get(self.user_token, {}).get('voice_enabled', False):
                    print(f"⚠️ [{self.custom_name}] Bị kick/rời khỏi Voice! Tiến hành nhảy lại vào Voice sau 5 giây...")
                    await asyncio.sleep(5)
                    await self.join_voice()

    # VÒNG LẶP CHECK ĐỊNH KỲ MỖI 60 GIÂY
    async def keep_voice_alive_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(60)
            if ACCOUNTS_DATA.get(self.user_token, {}).get('voice_enabled', False):
                try:
                    channel = self.get_channel(DEFAULT_VOICE_ID)
                    if channel:
                        guild = channel.guild
                        if guild and guild.me and guild.me.voice is None:
                            print(f"🔄 [{self.custom_name}] Phát hiện mất kết nối Voice. Đang Auto Join lại...")
                            await self.join_voice()
                except Exception as e:
                    pass

    # VÒNG LẶP AUTO DONATE HÀNG GIỜ (3600 GIÂY)
    async def hourly_donate_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(3600)
            if ACCOUNTS_DATA.get(self.user_token, {}).get('voice_enabled', False):
                try:
                    chat_channel = self.get_channel(CHAT_DONATE_CHANNEL_ID) or await self.fetch_channel(CHAT_DONATE_CHANNEL_ID)
                    if chat_channel:
                        print(f"💰 [{self.custom_name}] Đã treo đủ 1 giờ -> Tự động .donate cho Acc chính!")
                        await chat_channel.send(f".donate <@{MAIN_ACC_ID}> all")
                except Exception as e:
                    print(f"❌ [{self.custom_name}] Lỗi gửi lệnh donate: {e}")

async def start_new_account(token, name):
    bot = VoiceSelfBot(token=token, custom_name=name)
    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Lỗi Token {token[:12]}: {e}")
        ACCOUNTS_DATA[token]['status'] = "Lỗi Token"

bot_loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_forever()

Thread(target=start_loop, daemon=True).start()

async def main():
    token_string = os.getenv('DISCORD_TOKEN') or os.getenv('DISCORD-TOKEN') or ""
    tokens = [t.strip() for t in token_string.split(",") if t.strip()]

    for idx, token in enumerate(tokens):
        c_name = f"Acc {idx + 1}"
        ACCOUNTS_DATA[token] = {
            "name": c_name,
            "voice_enabled": True,
            "status": "Starting...",
            "bot_obj": None
        }
        asyncio.run_coroutine_threadsafe(start_new_account(token, c_name), bot_loop)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
