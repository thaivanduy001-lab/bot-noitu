import discord
import asyncio
import os
import re
import random
from threading import Thread
from flask import Flask, render_template_string, request, jsonify

# ==========================================
# CẤU HÌNH CƠ BẢN
# ==========================================
CHAT_GAME_CHANNEL_ID = 1531875015769854054  # ID Kênh chat chơi game Bom

ACCOUNTS_DATA = {}

app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Discord Game Bom Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #fff; margin: 0; padding: 20px; }
        h2 { color: #5865F2; text-align: center; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; }
        textarea { width: 100%; padding: 12px; background: #2b2b2b; color: #fff; border: 1px solid #444; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { background: #5865F2; color: #fff; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; font-size: 15px; margin-top: 10px; }
        button:hover { background: #4752C4; }
        .btn-delete { background: #ff4757; color: white; border: none; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 12px; float: right; }
        .acc-row { padding: 12px 0; border-bottom: 1px solid #2d2d2d; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .online { background: #2ed573; color: #000; }
        .offline { background: #ff4757; color: #fff; }
    </style>
</head>
<body>
    <h2>💣 DISCORD AUTO GAME BOM PANEL</h2>
    
    <div class="card">
        <h3>Thêm Token Acc Chơi Game</h3>
        <form action="/add_tokens" method="POST">
            <p><small style="color: #bbb;">Nhập mỗi Token trên 1 dòng (Dòng 1 là Acc 1 - Auto nhắn .bom, Dòng 2 là Acc 2):</small></p>
            <textarea name="token_list" rows="4" placeholder="Token_Acc_1&#10;Token_Acc_2"></textarea>
            <button type="submit">Lưu & Khởi Chạy Ngay</button>
        </form>
    </div>

    <div class="card">
        <h3>Danh Sách Account (Tổng: {{ accounts|length }})</h3>
        {% if not accounts %}
            <p style="color: #888; text-align: center;">Chưa có Token nào. Hãy dán Token vào ô bên trên!</p>
        {% endif %}
        {% for token, acc in accounts.items() %}
        <div class="acc-row">
            <button class="btn-delete" onclick="deleteAcc('{{ token }}')">Xóa</button>
            <strong>{{ acc.name }}</strong> 
            <span class="badge {{ 'online' if acc.status == 'Online' else 'offline' }}">{{ acc.status }}</span>
            <br><small style="color: #888;">Token: {{ token[:15] }}...</small>
        </div>
        {% endfor %}
    </div>

    <script>
        function deleteAcc(token) {
            if (confirm("Xóa tài khoản này?")) {
                fetch('/delete_account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token })
                }).then(() => location.reload());
            }
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
    lines = [l.strip() for l in raw_text.strip().split('\n') if l.strip()]
    
    for token in lines:
        if token not in ACCOUNTS_DATA or ACCOUNTS_DATA[token]['status'] not in ['Online', 'Starting...']:
            acc_index = len(ACCOUNTS_DATA) + 1
            custom_name = f"Acc {acc_index}"
            
            ACCOUNTS_DATA[token] = {
                "name": custom_name,
                "index": acc_index,
                "status": "Starting...",
                "bot_obj": None
            }
            asyncio.run_coroutine_threadsafe(start_new_account(token, acc_index), bot_loop)

    return "<script>alert('Đã thêm Token thành công!'); window.location.href='/';</script>"

@app.route('/delete_account', methods=['POST'])
def delete_account():
    data = request.json
    token = data.get('token')
    if token in ACCOUNTS_DATA:
        bot = ACCOUNTS_DATA[token].get('bot_obj')
        if bot:
            asyncio.run_coroutine_threadsafe(bot.close(), bot_loop)
        del ACCOUNTS_DATA[token]
        for idx, (t, acc) in enumerate(ACCOUNTS_DATA.items()):
            acc['index'] = idx + 1
    return jsonify({"status": "ok"})

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# ==========================================
# CƠ CHẾ BOT CHƠI BOM ĐỔI Ô LIÊN TỤC
# ==========================================
class BomGameBot(discord.Client):
    def __init__(self, token, acc_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_token = token
        self.acc_index = acc_index  # 1 là Acc 1 (Nhắn .bom), 2 là Acc 2
        self.game_count = 0         # Số ván game
        self.last_bomb_num = None   # Số bom nổ ván trước
        self.last_chosen_num = None # Lưu ô vừa bấm vòng trước để KHÔNG bấm trùng lại
        self.is_game_running = False

    async def on_ready(self):
        ACCOUNTS_DATA[self.user_token]['name'] = f"{self.user.name} (Acc {self.acc_index})"
        ACCOUNTS_DATA[self.user_token]['status'] = "Online"
        ACCOUNTS_DATA[self.user_token]['bot_obj'] = self
        print(f"🟢 [ONLINE] Acc {self.acc_index}: {self.user.name}")

        # Acc 1 tự nhắn .bom sau khi đăng nhập thành công
        if self.acc_index == 1:
            await asyncio.sleep(4)
            await self.send_bom_command()

    async def send_bom_command(self):
        try:
            channel = self.get_channel(CHAT_GAME_CHANNEL_ID) or await self.fetch_channel(CHAT_GAME_CHANNEL_ID)
            if channel:
                print(f"💬 [Acc 1] Gửi lệnh .bom...")
                await channel.send(".bom")
        except Exception as e:
            print(f"❌ [Acc 1] Lỗi gửi .bom: {e}")

    async def on_message(self, message):
        if message.channel.id != CHAT_GAME_CHANNEL_ID:
            return

        content_to_check = message.content or ""
        if message.embeds:
            for embed in message.embeds:
                if embed.description: content_to_check += " " + embed.description
                if embed.title: content_to_check += " " + embed.title
                for field in embed.fields: content_to_check += f" {field.name} {field.value}"

        # 1. GHI NHẬN SỐ BOM NỔ TỪ BOT-HEHE
        if "Ô có bom:" in content_to_check:
            match = re.search(r'Ô có bom:\s*Ô số\s*([1-9])', content_to_check)
            if match:
                self.last_bomb_num = int(match.group(1))
                print(f"🎯 [Acc {self.acc_index}] Ghi nhận BOM nổ ở Ô số: {self.last_bomb_num}")

        # 2. XÁC ĐỊNH VÁN GAME KẾT THÚC -> ACC 1 TỰ NHẮN .bom LẠI
        if any(kw in content_to_check.lower() for kw in ["trúng bom", "thua", "kết thúc", "chiến thắng", "toàn bộ vòng"]):
            if self.is_game_running:
                self.is_game_running = False
                print(f"🏁 Ván game kết thúc!")
                if self.acc_index == 1:
                    await asyncio.sleep(3)
                    await self.send_bom_command()

        # 3. AUTO BẤM NÚT
        if message.components:
            # Thu thập các nút bấm đang hiển thị (1-9)
            available_buttons = []
            join_btn = None

            for row in message.components:
                for component in row.children:
                    if component.label:
                        if any(kw in component.label.lower() for kw in ["tham gia", "join", "chơi", "vào"]):
                            join_btn = component
                        elif component.label.isdigit():
                            available_buttons.append(component)

            # A. Bấm Tham Gia
            if join_btn:
                self.is_game_running = True
                await asyncio.sleep(0.5 + self.acc_index * 0.4)
                try:
                    await join_btn.click()
                    self.game_count += 1
                    print(f"✅ [Acc {self.acc_index}] Đã Bấm Tham Gia (Ván {self.game_count})")
                except Exception as e:
                    pass

            # B. Bấm Chọn Số (Đảm bảo xoay vòng ô khác nhau liên tục)
            elif available_buttons:
                target_num = self.get_dynamic_target_number(available_buttons)
                
                # Tìm đúng button có số target_num để bấm
                for btn in available_buttons:
                    if int(btn.label) == target_num:
                        await asyncio.sleep(0.5 + self.acc_index * 0.4)
                        try:
                            await btn.click()
                            self.last_chosen_num = target_num  # Cập nhật ô vừa bấm
                            print(f"🎯 [Acc {self.acc_index}] BẤM SỐ: {target_num} (Ván {self.game_count})")
                        except Exception as e:
                            print(f"❌ [Acc {self.acc_index}] Lỗi bấm số {target_num}: {e}")
                        break

    # LOGIC CHỌN SỐ BIẾN ĐỔI LIÊN TỤC KHÔNG TRÙNG Ô CŨ
    def get_dynamic_target_number(self, available_buttons):
        valid_nums = [int(btn.label) for btn in available_buttons if btn.label.isdigit()]
        
        # 1. Nếu có dữ liệu ván trước:
        if self.last_bomb_num:
            # Ván 1-3: Chọn theo số bom nổ ván trước (nếu số đó nằm trong danh sách nút active)
            if self.game_count <= 3 and self.last_bomb_num in valid_nums:
                return self.last_bomb_num
            # Ván 4+: Acc 1 giữ bom nổ, Acc 2 nhảy sang số khác
            elif self.game_count > 3:
                if self.acc_index == 1 and self.last_bomb_num in valid_nums:
                    return self.last_bomb_num

        # 2. Trường hợp chưa có ván trước / Vòng 2,3,4 của cùng ván / Acc 2 tách số:
        # Tự động lọc danh sách ô khả thi (loại bỏ ô vừa mới bấm ở vòng trước)
        candidate_nums = [n for n in valid_nums if n != self.last_chosen_num]
        
        if not candidate_nums:
            candidate_nums = valid_nums

        # Nếu là Acc 2 ở ván > 3, dịch chuyển số khác Acc 1
        if self.acc_index == 2:
            return random.choice(candidate_nums)
        else:
            # Chọn ô tiếp theo liên tục để nhảy số (Ví dụ vừa chọn 1 -> chọn 2 -> chọn 3)
            if self.last_chosen_num and (self.last_chosen_num + 1) in candidate_nums:
                return self.last_chosen_num + 1
            return candidate_nums[0]

async def start_new_account(token, acc_index):
    bot = BomGameBot(token=token, acc_index=acc_index)
    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Lỗi Token Acc {acc_index}: {e}")
        if token in ACCOUNTS_DATA:
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
        acc_index = idx + 1
        c_name = f"Acc {acc_index}"
        ACCOUNTS_DATA[token] = {
            "name": c_name,
            "index": acc_index,
            "status": "Starting...",
            "bot_obj": None
        }
        asyncio.run_coroutine_threadsafe(start_new_account(token, acc_index), bot_loop)
        await asyncio.sleep(2)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
