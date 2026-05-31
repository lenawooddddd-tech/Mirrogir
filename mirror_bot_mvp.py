import os
import threading
from telethon import TelegramClient, events
import aiosqlite
from datetime import datetime
from flask import Flask

# 配置读取：使用环境变量，仅在本地开发环境下使用默认值以防报错
API_ID = int(os.environ.get("API_ID", 36675093))
API_HASH = os.environ.get("API_HASH", "06eb9ea66dba284800d6051af13971e2")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8611932078:AAGxyvuWAjNcJ0U4rQujqhwGKvgerCe0ZDQ")
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@Mirrogir")
DB_PATH = "mirror_data.db"

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is alive", 200


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# 初始化客户端
bot = TelegramClient('mirror_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def check_channel_membership(user_id: int) -> bool:
    """验证用户是否在目标频道内"""
    try:
        await bot.get_permissions(REQUIRED_CHANNEL, user_id)
        return True
    except Exception:
        return False

@bot.on(events.NewMessage)
async def handler(event):
    user_id = event.sender_id
    
    # 强制订阅校验
    if not await check_channel_membership(user_id):
        await event.reply(f"🔒 访问受限：请先订阅官方频道 {REQUIRED_CHANNEL} 后再进行对话。")
        return

    # 意图确认：当前处于 MVP 阶段，后续逻辑将通过 bot_engine.py 模块化接入
    await event.reply("🧠 镜像引擎在线，已解析你的意图。请发送目标言行以开始博弈分析。")

print("Mirror MVP Server Booting...")
threading.Thread(target=run_web, daemon=True).start()
bot.run_until_disconnected()