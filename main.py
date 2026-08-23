import discord
import asyncio
import re
import random
import os
import requests

CHANNEL_ID = 1531875015769854054  # Channel ID bạn cung cấp
BOT_HEHE_ID = None  # Sẽ tự động nhận diện hoặc kiểm tra tên/embed

client = discord.Client()

# Hàm tra từ điển ghép tiếng Việt từ nguồn API mở
def get_vietnamese_word(start_word):
    try:
        # Gọi API Wiktionary / Dictionary Tiếng Việt
        url = f"https://vi.wiktionary.org/w/api.php?action=opensearch&search={start_word}&limit=10&format=json"
        res = requests.get(url, timeout=5).json()
        suggestions = res[1]
        
        for word in suggestions:
            words = word.lower().split()
            # Tìm cụm từ đúng 2 tiếng bắt đầu bằng từ yêu cầu
            if len(words) == 2 and words[0] == start_word.lower():
                return word.lower()
    except Exception as e:
        print(f"Lỗi tra từ điển API: {e}")
    
    # Từ điển dự phòng thủ công cho các từ phổ biến
    backup_dict = {
        "mai": "mai sau",
        "sau": "sau này",
        "này": "này nọ",
        "nọ": "nọ kia",
        "kia": "kia kìa"
    }
    return backup_dict.get(start_word.lower(), None)

@client.event
async def on_ready():
    print(f"Đã đăng nhập thành công: {client.user}")
    # Bắt đầu vòng lặp gửi lệnh .nt mỗi 1 phút
    client.loop.create_task(send_nt_loop())

async def send_nt_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        try:
            channel = await client.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"Không tìm thấy Channel {CHANNEL_ID}: {e}")
            return

    while not client.is_closed():
        try:
            print("Đang tự động gửi lệnh .nt ...")
            await channel.send(".nt")
        except Exception as e:
            print(f"Lỗi gửi tin nhắn .nt: {e}")
        
        # Chờ 60 giây (1 phút) trước khi gõ lại
        await asyncio.sleep(60)

@client.event
async def on_message(message):
    # Chỉ đọc tin nhắn trong đúng Channel được chỉ định
    if message.channel.id != CHANNEL_ID:
        return

    # 1. Trường hợp đọc đề bài trong Embed (Khi bắt đầu game)
    if message.embeds:
        for embed in message.embeds:
            description = embed.description or ""
            fields_text = "".join([f"{f.name} {f.value}" for f in embed.fields])
            full_text = description + " " + fields_text
            
            # Tìm tiếng bắt đầu (VD: "bắt đầu bằng: sau")
            match = re.search(r"bắt đầu bằng:\s*([^\s\|]+)", full_text, re.IGNORECASE)
            if match:
                start_word = match.group(1).strip()
                await solve_and_reply(message.channel, start_word)
                return

    # 2. Trường hợp đọc lượt tiếp theo trong tin nhắn thường
    content = message.content or ""
    if "Tiếp theo phải bắt đầu bằng tiếng:" in content or "bắt đầu bằng tiếng:" in content:
        match = re.search(r"bắt đầu bằng tiếng:\s*([^\s\|]+)", content, re.IGNORECASE)
        if match:
            start_word = match.group(1).strip()
            await solve_and_reply(message.channel, start_word)

async def solve_and_reply(channel, start_word):
    print(f"Nhận diện tiếng cần nối: '{start_word}'")
    answer = get_vietnamese_word(start_word)
    
    if answer:
        # Delay ngẫu nhiên từ 1.5 - 3.5 giây để giả lập thao tác người thật
        delay = random.uniform(1.5, 3.5)
        await asyncio.sleep(delay)
        
        print(f"Đã tìm thấy từ: '{answer}' -> Đang gửi...")
        await channel.send(answer)
    else:
        print(f"Không tìm thấy từ ghép phù hợp cho tiếng: '{start_word}'")

# Lấy Token từ biến môi trường Render
client.run(os.getenv('DISCORD_TOKEN'))
