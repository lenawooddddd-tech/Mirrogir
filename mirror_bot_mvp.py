import os
import json
import asyncio
import aiosqlite
import time
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
from openai import AsyncOpenAI
from flask import Flask
from threading import Thread

# 配置项
API_ID = int(os.environ.get('TG_API_ID', 0))
API_HASH = os.environ.get('TG_API_HASH', '')
BOT_TOKEN = os.environ.get('TG_BOT_TOKEN', '')
REQUIRED_CHANNEL = os.environ.get('TG_CHANNEL', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# 初始化
bot = TelegramClient('mirror_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
llm = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
DB_PATH = "mirror_mvp.db"

# System Prompt
SYSTEM_PROMPT = """你现在是“认知行为沙盘系统”。以绝对的“利益与博弈视角”解析对手行为。
输出必须为严格合法的 JSON 对象：
{
  "perception": "洞察到的真实意图",
  "profile": "对方弱点及状态更新",
  "decision": "当前应采取的博弈决策",
  "outputs": ["(情绪标签) 话术1", "(情绪标签) 话术2", "(情绪标签) 话术3"],
  "warning": "若无风险留空"
}"""

# Flask 保活
app = Flask(__name__)
@app.route('/')
def home(): return "Mirror Bot Active"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date REAL)')
        await db.execute('CREATE TABLE IF NOT EXISTS memories (user_id INTEGER, role TEXT, content TEXT, timestamp REAL)')
        await db.commit()

async def manage_memory(uid, role, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO memories VALUES (?, ?, ?, ?)', (uid, role, content, time.time()))
        await db.execute('DELETE FROM memories WHERE user_id=? AND timestamp NOT IN (SELECT timestamp FROM memories WHERE user_id=? ORDER BY timestamp DESC LIMIT 16)', (uid, uid))
        await db.commit()

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("🧠 认知沙盘已部署。")

@bot.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))
async def handle(event):
    uid, text = event.sender_id, event.raw_text
    msg = await event.reply("⏳ `推理中...`")
    try:
        resp = await llm.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}],
            response_format={"type": "json_object"},
            temperature=0.4
        )
        data = json.loads(resp.choices[0].message.content)
        panel = f"👁 {data['perception']}\n\n♟️ {data['decision']}\n\n💬 话术:\n"
        for i, opt in enumerate(data['outputs']): panel += f"{i+1}. {opt}\n"
        await manage_memory(uid, "user", text)
        await manage_memory(uid, "assistant", resp.choices[0].message.content)
        await msg.edit(panel)
    except Exception as e:
        await msg.edit(f"⚠️ 解析熔断: `{str(e)[:40]}`")

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))), daemon=True).start()
    asyncio.get_event_loop().run_until_complete(init_db())
    bot.run_until_disconnected()
