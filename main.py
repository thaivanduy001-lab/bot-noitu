import discord
import asyncio
import re
import random
import os
import requests
from threading import Thread
from flask import Flask

# 1. ĐIỀN THÔNG TIN KÊNH VÀ ACC CHÍNH
SINGLE_CHANNEL_ID = 1531875015769854054  # <--- ID Kênh chơi game
MAIN_ACC_ID = 1326098743170170932        # <--- ID Discord Acc chính (để clone donate)

# Lưu danh sách Custom ID của các nút đã có người chọn để tránh chọn trùng
CLICKED_BUTTON_IDS = set()

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Game Bom 2 Acc Chon So Khac Nhau 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

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
    except Exception:
        pass

    backup_dict = {
        "được": "được việc", "việc": "việc làm", "làm": "làm ăn", "ăn": "ăn uống",
        "mai": "mai sau", "sau": "sau này", "này": "này nọ", "nọ": "nọ kia"
    }
    return backup_dict.get(start_word, f"{start_word} việc")

class SelfBotClient(discord.Client):
    def __init__(self, acc_name, is_main, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.acc_name = acc_name
        self.is_main = is_main
        self.clone_win_count = 0

    async def on_ready(self):
        print(f"=== [DA KET NOI] {self.acc_name}: {self.user} ===")
        if self.is_main:
            asyncio.create_task(self.main_acc_game_loop())

    async def main_acc_game_loop(self):
        await self.wait_until_ready()
        await asyncio.sleep(5)
        while not self.is_closed():
            try:
                channel = self.get_channel(SINGLE_CHANNEL_ID) or await self.fetch_channel(SINGLE_CHANNEL_ID)
                if channel:
                    print(f"[{self.acc_name}] Gui .bom va .nt...")
                    await channel.send(".bom")
                    await asyncio.sleep(2)
                    await channel.send(".nt")
            except Exception as e:
                print(f"[{self.acc_name}] Loi gui lenh: {e}")
            await asyncio.sleep(30)

    async def on_message(self, message):
        if message.channel.id != SINGLE_CHANNEL_ID:
            return

        # Reset bộ nhớ nút đã bấm khi bắt đầu game mới
        if ".bom" in message.content.lower():
            CLICKED_BUTTON_IDS.clear()

        # Kiểm tra lượt thắng của Clone để Auto Donate
        if not self.is_main and ("thắng" in message.content.lower() or "winner" in message.content.lower()):
            if str(self.user.id) in message.content or (self.user.name and self.user.name.lower() in message.content.lower()):
                self.clone_win_count += 1
                print(f"🔥 [{self.acc_name}] Thang Game Bom! ({self.clone_win_count}/5)")
                
                if self.clone_win_count >= 5:
                    print(f"💰 [{self.acc_name}] Thang 5 lan -> Auto .donate cho Acc chinh!")
                    await asyncio.sleep(2)
                    await message.channel.send(f".donate <@{MAIN_ACC_ID}> all")
                    self.clone_win_count = 0

        # Xử lý Game Bom
        if message.components:
            await self.handle_bomb_buttons(message)

        if message.author.id == self.user.id:
            return

        # Xử lý Nối từ
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
            answer = get_vietnamese_word(start_word)
            if answer:
                await asyncio.sleep(random.uniform(1.2, 2.5))
                await message.channel.send(answer)

    async def handle_bomb_buttons(self, message):
        available_buttons = []
        
        # Lọc ra những Button chưa bị disable và CHƯA BỊ ACC KIA CHỌN
        for row in message.components:
            for component in row.children:
                if (component.type == discord.ComponentType.button 
                    and not component.disabled 
                    and component.custom_id not in CLICKED_BUTTON_IDS):
                    available_buttons.append(component)

        if available_buttons:
            # Phân tách thời gian bấm ngẫu nhiên để 2 acc không bấm trùng khoảnh khắc
            delay = random.uniform(1.0, 1.8) if self.is_main else random.uniform(2.0, 3.2)
            await asyncio.sleep(delay)

            # Lọc lại lần nữa phòng trường hợp Acc kia vừa chọn xong trong lúc chờ delay
            valid_buttons = [b for b in available_buttons if b.custom_id not in CLICKED_BUTTON_IDS]
            
            if valid_buttons:
                chosen_button = random.choice(valid_buttons)
                # Đánh dấu nút này đã được chọn
                CLICKED_BUTTON_IDS.add(chosen_button.custom_id)
                
                print(f"[{self.acc_name}] Chon nut so: {chosen_button.label or 'Unknow'}")
                try:
                    await chosen_button.click()
                except Exception:
                    pass

    async def on_message_edit(self, before, after):
        if after.channel.id == SINGLE_CHANNEL_ID and after.components:
            await self.handle_bomb_buttons(after)

async def main():
    token_string = os.getenv('DISCORD_TOKEN') or os.getenv('DISCORD-TOKEN') or ""
    tokens = [t.strip() for t in token_string.split(",") if t.strip()]

    if len(tokens) < 2:
        print("LỖI: Chưa đủ 2 Token!")
        return

    acc_main = SelfBotClient(acc_name="Acc Chinh", is_main=True)
    acc_clone = SelfBotClient(acc_name="Acc Clone", is_main=False)

    await asyncio.gather(
        acc_main.start(tokens[0]),
        acc_clone.start(tokens[1])
    )

asyncio.run(main())
