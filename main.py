import discord
import asyncio
import os
import re
from threading import Thread
from flask import Flask, render_template_string

# ==========================================
# CẤU HÌNH CƠ BẢN
# ==========================================
CHAT_GAME_CHANNEL_ID = 1531875015769854054  # ID Kênh chat chơi game Bom

ACCOUNTS_DATA = {}

app = Flask(__name__)

# Dashboard đơn giản xem trạng thái Bot
HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Discord Game Bom Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #121212; color: #fff; padding: 20px; }
        .card { background: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
        .status { padding: 3px 8px; border-radius: 4px; font-weight: bold; }
        .online { background: #2ed573; color: #000; }
        .offline { background: #ff4757; color: #fff; }
    </style>
</head>
<body>
    <h2>💣 DISCORD AUTO GAME BOM PANEL</h2>
    <div class="card">
        <h3>Trạng thái Bot Game (Tổng: {{ accounts|length }})</h3>
        {% for token, acc in accounts.items() %}
            <p><strong>{{ acc.name }}</strong> - <span class="status {{ 'online' if acc.status == 'Online' else 'offline' }}">{{ acc.status }}</span></p>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_DASHBOARD, accounts=ACCOUNTS_DATA)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# ==========================================
# CƠ CHẾ BOT CHƠI BOM THÔNG MINH (NO DONATE)
# ==========================================
class BomGameBot(discord.Client):
    def __init__(self, token, acc_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_token = token
        self.acc_index = acc_index # 1 là Acc 1, 2 là Acc 2
        self.game_count = 0        # Đếm số ván đã chơi
        self.last_bomb_num = None  # Số bom nổ ván trước (1-9)

    async def on_ready(self):
        ACCOUNTS_DATA[self.user_token]['name'] = f"{self.user.name} (Acc {self.acc_index})"
        ACCOUNTS_DATA[self.user_token]['status'] = "Online"
        print(f"🟢 [ONLINE] Bot Game Acc {self.acc_index}: {self.user.name}")

    async def on_message(self, message):
        # Chỉ xử lý trong đúng kênh game
        if message.channel.id != CHAT_GAME_CHANNEL_ID:
            return

        # 1. PHÁT HIỆN LỆNH .bom ĐỂ BẮT ĐẦU VÁN MỚI
        if message.content.strip().lower() == ".bom":
            print(f"💣 Phát hiện lệnh .bom từ {message.author.name}")

        # 2. KIỂM TRA KẾT QUẢ VÁN TRƯỚC (XÁC ĐỊNH VỊ TRÍ BOM NỔ)
        content_to_check = message.content or ""
        if message.embeds:
            for embed in message.embeds:
                if embed.description: content_to_check += " " + embed.description
                if embed.title: content_to_check += " " + embed.title

        # Lọc vị trí bom nổ (Ví dụ: "nổ tại số 5")
        if "nổ" in content_to_check.lower() or "bomb" in content_to_check.lower():
            numbers = re.findall(r'\b[1-9]\b', content_to_check)
            if numbers:
                self.last_bomb_num = int(numbers[0])
                print(f"💥 [Acc {self.acc_index}] Bom ván trước nổ ở số: {self.last_bomb_num}")

        # 3. TỰ ĐỘNG BẤM NÚT THAM GIA & CHỌN SỐ
        if message.components:
            for row in message.components:
                for component in row.children:
                    # A. Nút Bấm Tham Gia Game
                    if component.label and any(kw in component.label.lower() for kw in ["tham gia", "join", "chơi", "vào"]):
                        await asyncio.sleep(1 + self.acc_index * 0.5)
                        try:
                            await component.click()
                            self.game_count += 1
                            print(f"✅ [Acc {self.acc_index}] Đã vào chơi! (Ván {self.game_count})")
                        except Exception as e:
                            print(f"❌ [Acc {self.acc_index}] Lỗi bấm nút tham gia: {e}")

                    # B. Nút Bấm Chọn Số (1-9)
                    elif component.label and component.label.isdigit():
                        btn_num = int(component.label)
                        target_num = self.calculate_target_number()

                        if btn_num == target_num:
                            await asyncio.sleep(1 + self.acc_index * 0.4)
                            try:
                                await component.click()
                                print(f"🎯 [Acc {self.acc_index}] Chọn số {btn_num} ở Ván {self.game_count}")
                            except Exception as e:
                                print(f"❌ [Acc {self.acc_index}] Lỗi chọn số {btn_num}: {e}")

    # THUẬT TOÁN CHỌN SỐ (VÁN 1-3 ĐỊ GỒM, VÁN 4 TÁCH RA)
    def calculate_target_number(self):
        if not self.last_bomb_num:
            return 1

        # Ván 1, 2, 3: Cả 2 Acc đều chọn đúng số bom nổ ván trước
        if self.game_count <= 3:
            return self.last_bomb_num
        # Từ Ván 4 trở đi: Tách ra không chọn trùng
        else:
            if self.acc_index == 1:
                return self.last_bomb_num
            else:
                next_num = self.last_bomb_num + 1
                return 1 if next_num > 9 else next_num

async def start_new_account(token, acc_index):
    bot = BomGameBot(token=token, acc_index=acc_index)
    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Lỗi Token Acc {acc_index}: {e}")
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
            "status": "Starting...",
            "bot_obj": None
        }
        asyncio.run_coroutine_threadsafe(start_new_account(token, acc_index), bot_loop)
        await asyncio.sleep(2)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
