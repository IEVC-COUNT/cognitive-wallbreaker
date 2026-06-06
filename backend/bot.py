"""
认知破壁机 V2.0 — Telegram Bot
使用 python-telegram-bot v20+ 异步框架
"""
import os
import re
import json
import asyncio
import logging
from typing import Optional, List
from io import BytesIO

from telegram import (
    Bot,
    Update,
    Message,
    InputFile,
)
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.helpers import escape_markdown

from engine import (
    CognitiveEngine,
    SimulationInput,
    EngineConfig,
    encode_image_bytes_to_base64,
    get_image_mime_type,
)
from memory_manager import MemoryManager

# ═══════════════════════════════════════════
# 日志
# ═══════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("WallbreakerBot")

# ═══════════════════════════════════════════
# 配置（从环境变量读取）
# ═══════════════════════════════════════════

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-39d2be9a198742978eb9cabc3cc5bf05")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:4000/v1")
WALLBREAKER_MODEL = os.getenv("WALLBREAKER_MODEL", "deepseek-v4-flash")

# ═══════════════════════════════════════════
# 全局实例
# ═══════════════════════════════════════════

engine_config = EngineConfig(
    model=WALLBREAKER_MODEL,
    temperature=0.7,
    max_tokens=4096,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# 用户 → MemoryManager 映射
memory_managers: dict[int, MemoryManager] = {}


def get_user_memory(user_id: int) -> MemoryManager:
    """获取用户的记忆管理器"""
    uid = str(user_id)
    if user_id not in memory_managers:
        memory_managers[user_id] = MemoryManager(
            user_id=uid,
            openai_api_key=OPENAI_API_KEY,
            openai_base_url=OPENAI_BASE_URL,
        )
    return memory_managers[user_id]


def get_user_engine(user_id: int) -> CognitiveEngine:
    """获取用户的推演引擎"""
    return CognitiveEngine(
        config=engine_config,
        memory_manager=get_user_memory(user_id),
    )


# ═══════════════════════════════════════════
# Markdown 工具函数
# ═══════════════════════════════════════════

TELEGRAM_MAX_LENGTH = 4096
TELEGRAM_HTML_MAX_LENGTH = 3072  # HTML 解析模式有更低限制


def split_long_message(
    text: str,
    max_length: int = TELEGRAM_MAX_LENGTH,
) -> List[str]:
    """
    将长文本按 Telegram 限制分割成多个段落

    分割策略：
    1. 优先在标题行（## 开头）处分割
    2. 其次在双换行符处分割
    3. 最后在句号处分割
    4. 兜底：强制截断

    Args:
        text: 原始文本
        max_length: 每段最大字符数

    Returns:
        分割后的文本段落列表
    """
    if len(text) <= max_length:
        return [text]

    chunks = []

    # 按标题分割
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)

    current_chunk = ""
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 如果当前段落 + 新段落不超过限制，合并
        if len(current_chunk) + len(section) + 2 <= max_length:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
        else:
            # 当前段落已满，先保存
            if current_chunk:
                chunks.append(current_chunk)

            # 如果新段落本身超过限制，需要进一步分割
            if len(section) <= max_length:
                current_chunk = section
            else:
                # 按段落分割超长 section
                sub_chunks = _split_by_paragraph(section, max_length)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""

    # 添加最后一段
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_by_paragraph(text: str, max_length: int) -> List[str]:
    """按段落和句子分割超长文本"""
    chunks = []

    # 先按空行分割
    paragraphs = text.split("\n\n")

    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= max_length:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)

            if len(para) > max_length:
                # 按句子强制分割
                sentences = re.split(r"(?<=[。！？\.\!\?])", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) <= max_length:
                        current += sent
                    else:
                        if current:
                            chunks.append(current)
                        if len(sent) > max_length:
                            # 最后手段：强制截断
                            for i in range(0, len(sent), max_length):
                                chunks.append(sent[i:i + max_length])
                            current = ""
                        else:
                            current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


def escape_md(text: str) -> str:
    """
    转义 Telegram MarkdownV2 特殊字符

    参考: https://core.telegram.org/bots/api#markdownv2-style

    Args:
        text: 原始文本

    Returns:
        转义后的文本
    """
    # 需要转义的字符
    special_chars = r"_*[]()~`>#+-=|{}.!"
    escape_map = {c: f"\\{c}" for c in special_chars}

    result = []
    in_code_block = False

    for line in text.split("\n"):
        stripped = line.strip()
        # 不在代码块内时才转义
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            # 代码块标记本身也需要转义反引号
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # 转义特殊字符（但保护已有的 Markdown 格式）
        escaped = ""
        i = 0
        while i < len(line):
            c = line[i]

            # 跳过已有的 Markdown 格式标记
            # 粗体 **text**
            if c == "*" and i + 1 < len(line) and line[i + 1] == "*":
                escaped += "**"
                i += 2
                continue

            # 链接格式 [text](url)
            if c == "[" and "]" in line[i:] and "(" in line[i:]:
                end = line.find("]", i)
                url_start = line.find("(", end)
                url_end = line.find(")", url_start)
                if end > i and url_start > end and url_end > url_start:
                    link_text = line[i + 1:end]
                    link_url = line[url_start + 1:url_end]
                    escaped += f"[{link_text}]({link_url})"
                    i = url_end + 1
                    continue

            if c in escape_map:
                escaped += escape_map[c]
            else:
                escaped += c
            i += 1

        result.append(escaped)

    return "\n".join(result)


def apply_basic_formatting(text: str) -> str:
    """
    应用基本 Markdown 格式，用于 HTML parse mode

    将 **粗体** 转换为 <b>粗体</b>
    将 *斜体* 转换为 <i>斜体</i>
    将 `代码` 转换为 <code>代码</code>

    Args:
        text: 原始 Markdown 文本

    Returns:
        HTML 格式化文本
    """
    # 保护代码块
    code_blocks = []
    def save_code(m):
        code_blocks.append(m.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    text = re.sub(r"```[\s\S]*?```", save_code, text)
    text = re.sub(r"`([^`]+)`", save_code, text)

    # 粗体
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # 斜体
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

    # 恢复代码块
    for i, block in enumerate(code_blocks):
        marker = f"__CODE_BLOCK_{i}__"
        if block.startswith("```"):
            lang_content = block[3:-3].strip()
            if "\n" in lang_content:
                first_line, rest = lang_content.split("\n", 1)
                text = text.replace(marker, f"<pre><code>{rest}</code></pre>")
            else:
                text = text.replace(marker, f"<pre><code>{lang_content}</code></pre>")
        else:
            text = text.replace(marker, f"<code>{block[1:-1]}</code>")

    return text


# ═══════════════════════════════════════════
# Bot 命令处理
# ═══════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    welcome_text = (
        f"🧠 *认知破壁机 V2.0* — 欢迎你，{user.first_name or '朋友'}。\n\n"
        f"我是你的个人决策推演引擎。\n"
        f"把任何让你纠结的决策发送给我，我会用四把「思维手术刀」帮你深度剖析：\n\n"
        f"🔪 击碎隐性假设\n"
        f"🌊 推演二阶涟漪效应\n"
        f"👁️ 揭露第三方利益暗面\n"
        f"🎭 生成反直觉剧本\n\n"
        f"*使用方法*\n"
        f"• 直接发送文字描述你的决策困境\n"
        f"• 也可以发送截图/图片辅助分析\n"
        f"• 输入 /reset 清除你的历史记忆\n"
        f"• 输入 /stats 查看你的决策分析统计\n\n"
        f"现在，告诉我你在纠结什么？"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /reset 命令 — 清除记忆"""
    user_id = update.effective_user.id
    mem = get_user_memory(user_id)
    mem.clear_user_memories()
    await update.message.reply_text(
        "🗑️ 你的历史记忆已清除。一切重新开始。",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /stats 命令 — 显示记忆统计"""
    user_id = update.effective_user.id
    mem = get_user_memory(user_id)
    stats = mem.stats()

    text = (
        f"📊 *你的决策分析统计*\n\n"
        f"• 总记忆数：{stats['total_memories']} 条\n"
        f"• 记忆引擎：{'Mem0 语义搜索' if stats['mem0_enabled'] else '本地关键词匹配'}\n"
        f"• 最近更新：{stats['last_updated'] or '暂无'}\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = (
        "*认知破壁机 · 命令列表*\n\n"
        "/start — 重新开始\n"
        "/reset — 清除我的历史记忆\n"
        "/stats — 查看分析统计\n"
        "/help — 显示此帮助\n\n"
        "直接发送文字或图片即可开始分析。"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)


# ═══════════════════════════════════════════
# 消息处理核心
# ═══════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户消息（文本 + 图片混合）"""
    user = update.effective_user
    message = update.message

    user_id = user.id

    # 收集文本
    text = message.text or message.caption or ""

    # 收集图片
    images_base64 = []
    if message.photo:
        # Telegram 发送多分辨率版本，取最大的
        best_photo = message.photo[-1]
        photo_file = await context.bot.get_file(best_photo.file_id)
        photo_bytes = BytesIO()
        await photo_file.download_to_memory(photo_bytes)
        photo_data = photo_bytes.getvalue()
        mime_type = get_image_mime_type(photo_data)
        img_b64 = encode_image_bytes_to_base64(photo_data)
        images_base64.append(f"data:{mime_type};base64,{img_b64}")

    # 没有文字也没有图片
    if not text.strip() and not images_base64:
        await message.reply_text(
            "请发送文字描述你的决策困境，或发送一张相关的图片。",
        )
        return

    # 发送"正在思考"状态
    thinking_msg = await message.reply_text(
        "🧠 *正在深度推演中...*\n"
        "🔍 检索你的历史决策记忆\n"
        "🔪 击碎隐性假设\n"
        "🌊 推动涟漪效应\n"
        "👁️ 分析利益暗面\n"
        "🎭 生成反直觉剧本\n\n"
        "_预计需要 15-30 秒，请耐心等待..._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    # 发送"正在输入"状态
    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING,
    )

    try:
        # 构建输入
        user_input = SimulationInput(
            user_id=str(user_id),
            text=text.strip() if text.strip() else "请分析这张图片",
            images_base64=images_base64 if images_base64 else None,
        )

        # 获取引擎
        engine = get_user_engine(user_id)

        # 收集流式结果
        full_text = ""
        async for data in engine.simulate_stream(user_input):
            if data.startswith("data: "):
                try:
                    payload = json.loads(data[6:])
                    if payload.get("type") == "content":
                        full_text += payload.get("text", "")
                except json.JSONDecodeError:
                    continue

        # 更新思考消息为完成状态
        if full_text:
            # 删除"正在思考"消息
            await thinking_msg.delete()

            # 分割长文本
            chunks = split_long_message(full_text)

            # 逐个发送分段
            for i, chunk in enumerate(chunks):
                try:
                    # 尝试使用 HTML 格式
                    formatted = apply_basic_formatting(chunk)

                    if i == 0:
                        # 第一段：带标题
                        header = f"🧠 *认知破壁机分析报告*\n\n"
                        await message.reply_text(
                            header + chunk,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                    elif len(formatted) <= TELEGRAM_HTML_MAX_LENGTH:
                        try:
                            await message.reply_text(
                                chunk,
                                parse_mode=ParseMode.MARKDOWN_V2,
                            )
                        except Exception:
                            # 回退到纯文本
                            await message.reply_text(chunk)
                    else:
                        # 纯文本发送
                        await message.reply_text(chunk)

                    # 段落间延迟，避免被封
                    if len(chunks) > 1 and i < len(chunks) - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Markdown parse failed for chunk {i}: {e}")
                    # 回退：纯文本发送
                    try:
                        await message.reply_text(chunk)
                    except Exception:
                        await message.reply_text(chunk[:TELEGRAM_MAX_LENGTH])

        else:
            # 推演失败
            await thinking_msg.edit_text(
                "❌ 推演出错：未能生成分析结果。请稍后重试。",
            )

    except Exception as e:
        logger.error(f"Wallbreaker error for user {user_id}: {e}")
        try:
            await thinking_msg.edit_text(
                f"❌ 推演出错：{str(e)[:200]}\n\n请稍后重试，或联系管理员。",
            )
        except Exception:
            await message.reply_text(
                f"❌ 推演出错，请稍后重试。",
            )


# ═══════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════

def main():
    """启动 Telegram Bot"""
    if not TELEGRAM_TOKEN:
        logger.error(
            "未设置 TELEGRAM_BOT_TOKEN 环境变量！\n"
            "请设置: export TELEGRAM_BOT_TOKEN=你的Bot Token"
        )
        return

    # 创建 Application
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))

    # 注册消息处理器（文本 + 图片）
    application.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.CAPTION,
            handle_message,
        )
    )

    logger.info("🧠 认知破壁机 Telegram Bot 启动中...")
    logger.info(f"   模型: {WALLBREAKER_MODEL}")
    logger.info(f"   API: {OPENAI_BASE_URL}")

    # 启动轮询
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
