"""
认知破壁机 V6.0 — Telegram Bot
支持 /simulate 推演、/v5 多Agent、/dual 双路对比
使用原生 Telegram Bot API (httpx)，无需额外依赖
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx

# 加载 .env
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path, override=True)
except ImportError:
    pass

from engine import CognitiveEngine, SimulationInput, EngineConfig
from memory_manager import MemoryManager

# ═══════════════════════════════════════════
# 日志
# ═══════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("wallbreaker-bot")

# ═══════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

API_KEY = os.getenv("OPENAI_API_KEY", "sk-39d2be9a198742978eb9cabc3cc5bf05")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("WALLBREAKER_MODEL", "deepseek-chat")

# 单次推演最大字符数 (Telegram 消息限制约 4096)
MAX_RESPONSE_CHARS = 3800

# ═══════════════════════════════════════════
# 引擎实例（共享）
# ═══════════════════════════════════════════
engine_config = EngineConfig(
    model=MODEL,
    temperature=0.7,
    max_tokens=2048,
    api_key=API_KEY,
    base_url=BASE_URL,
)

# 按 user_id 缓存引擎实例
_engines: dict[str, CognitiveEngine] = {}
_memories: dict[str, MemoryManager] = {}


def get_engine(user_id: str) -> CognitiveEngine:
    if user_id not in _engines:
        mem = MemoryManager(
            user_id=user_id,
            openai_api_key=API_KEY,
            openai_base_url=BASE_URL,
            storage_dir=os.path.join(os.path.dirname(__file__), "..", "data", "memory"),
        )
        _engines[user_id] = CognitiveEngine(config=engine_config, memory_manager=mem)
    return _engines[user_id]


# ═══════════════════════════════════════════
# Telegram API 封装
# ═══════════════════════════════════════════

async def tg_send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
    """发送消息到 Telegram"""
    # 截断过长消息
    if len(text) > MAX_RESPONSE_CHARS:
        text = text[:MAX_RESPONSE_CHARS] + "\n\n…[已截断]"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
        )
        return resp.json()


async def tg_send_chat_action(chat_id: int, action: str = "typing") -> None:
    """发送"正在输入…"状态"""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
        )


async def tg_get_updates(offset: Optional[int] = None, timeout: int = 30) -> list:
    """长轮询获取更新"""
    params = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        resp = await client.post(f"{TELEGRAM_API}/getUpdates", json=params)
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
        return []


# ═══════════════════════════════════════════
# 命令处理
# ═══════════════════════════════════════════

WELCOME_TEXT = """🧠 *认知破壁机 V6.0*

击碎隐性假设，穿透认知盲区。

*命令列表:*
/simulate <决策> — 五刀推演（快速）
/v5 <决策> — 查看多Agent模式说明
/help — 帮助信息

直接发送决策文本即可开始推演 🔪"""

HELP_TEXT = """🔪 *认知破壁机 — 使用指南*

*直接发送*你的决策困境，引擎将进行五刀推演：
1️⃣ 心理防御与认知盲区
2️⃣ 利益链条与收割逻辑
3️⃣ 阶层筹码与容错率
4️⃣ 灰度博弈与反向操作
5️⃣ 终极破壁拷问

*提示：*
• 描述越具体，分析越精准
• 支持上传图片（OCR识别文字）
• 完整功能请使用 Web 端: http://localhost:3000

⚠️ 推演结果仅供参考，最终决策权在你手中。"""


async def handle_start(chat_id: int) -> None:
    await tg_send_message(chat_id, WELCOME_TEXT)


async def handle_help(chat_id: int) -> None:
    await tg_send_message(chat_id, HELP_TEXT)


async def handle_simulate(chat_id: int, user_id: str, text: str) -> None:
    """执行推演并发送结果"""
    if not text.strip():
        await tg_send_message(chat_id, "❌ 请提供具体的决策描述。例如：\n`/simulate 要不要裸辞创业`")
        return

    # 发送"正在输入…"
    await tg_send_chat_action(chat_id, "typing")

    # 发送进度提示
    progress_msg = await tg_send_message(chat_id, "🔍 *正在启动认知破壁引擎…*")

    engine = get_engine(user_id)
    user_input = SimulationInput(user_id=user_id, text=text.strip())

    try:
        # 非流式收集完整输出
        full_text = ""
        async for data in engine.simulate_stream(user_input):
            if data.startswith("data: "):
                try:
                    payload = json.loads(data[6:])
                    if payload.get("type") == "content":
                        full_text += payload.get("text", "")
                except json.JSONDecodeError:
                    continue

        if full_text.strip():
            # 删除进度消息，发送结果
            progress_id = progress_msg.get("result", {}).get("message_id", 0)
            if progress_id:
                async with httpx.AsyncClient(timeout=10) as c:
                    await c.post(f"{TELEGRAM_API}/deleteMessage", json={
                        "chat_id": chat_id,
                        "message_id": progress_id,
                    })

            # 分段发送（Telegram 单条消息 4096 字符限制）
            await send_long_message(chat_id, full_text)
        else:
            await tg_send_message(chat_id, "❌ 推演引擎未返回有效结果，请稍后重试。")

    except Exception as e:
        log.error(f"推演异常: {e}")
        await tg_send_message(chat_id, f"❌ 推演出错: {str(e)[:200]}")


async def send_long_message(chat_id: int, text: str) -> None:
    """分段发送长消息"""
    # 按 3800 字符分段，在段落边界处切割
    if len(text) <= MAX_RESPONSE_CHARS:
        await tg_send_message(chat_id, text)
        return

    paragraphs = text.split("\n\n")
    chunk = ""
    for para in paragraphs:
        if len(chunk) + len(para) + 2 > MAX_RESPONSE_CHARS:
            if chunk:
                await tg_send_message(chat_id, chunk)
                chunk = para
            else:
                # 单段超长，硬切割
                await tg_send_message(chat_id, para[:MAX_RESPONSE_CHARS])
                if len(para) > MAX_RESPONSE_CHARS:
                    chunk = para[MAX_RESPONSE_CHARS:]
                else:
                    chunk = ""
        else:
            chunk = (chunk + "\n\n" + para) if chunk else para
    if chunk:
        await tg_send_message(chat_id, chunk)


# ═══════════════════════════════════════════
# 消息路由
# ═══════════════════════════════════════════

async def process_message(msg: dict) -> None:
    """处理单条消息"""
    chat = msg.get("chat", {})
    from_user = msg.get("from", {})
    chat_id = chat.get("id", 0)
    user_id = str(from_user.get("id", "unknown"))
    text = msg.get("text", "").strip()

    if not text:
        return

    log.info(f"[{user_id}] {text[:100]}")

    # 命令路由
    if text.startswith("/start"):
        await handle_start(chat_id)
    elif text.startswith("/help"):
        await handle_help(chat_id)
    elif text.startswith("/simulate"):
        query = text[len("/simulate"):].strip()
        await handle_simulate(chat_id, user_id, query)
    elif text.startswith("/v5"):
        await tg_send_message(
            chat_id,
            "😈 *V5.0 多智能体对抗模式*\n\n"
            "7 Agent 完整推演需要约 2-3 分钟，建议在 Web 端使用：\n"
            "http://localhost:3000\n\n"
            "Bot 端当前使用 V4.0 单引擎快速推演（约 15 秒），"
            "直接发送决策文本即可。",
        )
    else:
        # 默认当作推演请求
        await handle_simulate(chat_id, user_id, text)


# ═══════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════

async def main():
    if not TELEGRAM_TOKEN:
        log.error("❌ TELEGRAM_BOT_TOKEN 未设置！请在 .env 中配置")
        log.error("   示例: TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjkl")
        log.error("   获取 Token: https://t.me/BotFather")
        return

    log.info("=" * 50)
    log.info("  认知破壁机 V6.0 · Telegram Bot")
    log.info(f"  Model: {MODEL}")
    log.info(f"  API: {BASE_URL}")
    log.info("=" * 50)

    # 验证 Token
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{TELEGRAM_API}/getMe")
        data = resp.json()
        if data.get("ok"):
            bot_info = data.get("result", {})
            log.info(f"  ✅ Bot 已连接: @{bot_info.get('username')}")
        else:
            log.error(f"  ❌ Token 无效: {data.get('description')}")
            return

    log.info("  📡 开始监听消息...")
    log.info("=" * 50)

    offset = 0
    while True:
        try:
            updates = await tg_get_updates(offset=offset, timeout=25)
            for update in updates:
                update_id = update.get("update_id", 0)
                offset = max(offset, update_id + 1)

                msg = update.get("message")
                if msg:
                    asyncio.create_task(process_message(msg))

        except asyncio.CancelledError:
            log.info("Bot 已停止")
            break
        except Exception as e:
            log.error(f"轮询异常: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("收到中断信号，Bot 退出")
