"""
认知破壁机 V6.0 — 多平台事件采集管道
从各平台采集真实个人决策事件，LLM筛选后自动推演入库

数据源:
  - Reddit: r/ShouldI, r/makemychoice, r/Advice (免费JSON API)
  - V2EX: 问与答板块 (HTML解析)
"""
import json
import asyncio
import re
import os
import time
import uuid
from datetime import datetime, timezone
from html import unescape
from typing import Optional, List

import httpx
from openai import AsyncOpenAI

from database import get_db
from public_api import generate_title, parse_topology, save_anonymous_memory

# ═══════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════

API_KEY = os.getenv("OPENAI_API_KEY", "sk-39d2be9a198742978eb9cabc3cc5bf05")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:4000/v1")
MODEL = os.getenv("WALLBREAKER_MODEL", "deepseek-v4-flash")

SOURCES = {
    "reddit_shouldi": {
        "name": "Reddit r/ShouldI",
        "urls": [
            "https://www.reddit.com/r/ShouldI/new.json?limit=10",
            "https://www.reddit.com/r/makemychoice/new.json?limit=10",
            "https://www.reddit.com/r/Advice/new.json?limit=10",
        ],
        "type": "json",
    },
    "v2ex": {
        "name": "V2EX 问与答",
        "urls": ["https://www.v2ex.com/api/topics/latest.json"],
        "type": "json",
    },
}

# LLM 决策分类 Prompt
DECISION_CLASSIFIER_PROMPT = """你是一个帖子分类器。判断以下帖子内容是否是"个人决策/人生抉择/犹豫选择"类问题。

是个人决策的特征：
- 面临选择：跳槽、买房、投资、转行、分手、搬家、要不要做某事
- 带有犹豫：该不该、要不要、怎么选、帮忙拿主意
- 涉及人生重要抉择

不是的特征：
- 纯技术问题、教程、评价、新闻、吐槽、广告
- 已经做了决定只是分享经验

只回答 YES 或 NO，不要解释。

帖子标题: {title}
帖子内容: {content}"""


# ═══════════════════════════════════════════
# 数据源采集器
# ═══════════════════════════════════════════

async def fetch_reddit_posts(subreddit_url: str) -> list[dict]:
    """从 Reddit JSON API 获取帖子列表"""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                subreddit_url,
                headers={"User-Agent": "Mozilla/5.0 Wallbreaker/6.0 (Data Collector)"},
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            results = []
            for p in posts:
                d = p.get("data", {})
                title = d.get("title", "")
                content = d.get("selftext", "")
                if title:
                    results.append({
                        "title": title.strip(),
                        "content": content.strip()[:500] if content else title.strip(),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "source": "reddit",
                        "author": d.get("author", ""),
                    })
            return results
    except Exception:
        return []


async def fetch_v2ex_posts() -> list[dict]:
    """从 V2EX 最新API获取帖子列表"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.v2ex.com/api/topics/latest.json",
                headers={"User-Agent": "Mozilla/5.0 Wallbreaker/6.0"},
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            results = []
            for t in data[:30]:
                title = t.get("title", "")
                content = t.get("content", "")
                if title:
                    results.append({
                        "title": title.strip(),
                        "content": (content or "").strip()[:500],
                        "url": t.get("url", ""),
                        "source": "v2ex",
                        "author": t.get("member", {}).get("username", ""),
                    })
            return results
    except Exception:
        return []


# ═══════════════════════════════════════════
# LLM 筛选器 + 自动推演
# ═══════════════════════════════════════════

async def classify_decision(client: AsyncOpenAI, title: str, content: str) -> bool:
    """用 LLM 判断帖子是否是个人决策问题"""
    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=MODEL, temperature=0.0, max_tokens=5,
                messages=[{
                    "role": "user",
                    "content": DECISION_CLASSIFIER_PROMPT.format(title=title[:200], content=content[:300])
                }],
            ), timeout=10,
        )
        answer = resp.choices[0].message.content.strip().upper()
        return answer.startswith("YES") or answer.startswith("是")
    except Exception:
        return False


async def auto_deduce_and_save(client: AsyncOpenAI, post: dict) -> Optional[str]:
    """
    自动推演一条帖子：调用 V4 引擎，保存到 SQLite
    返回 event_id 或 None
    """
    from engine import CognitiveEngine, SimulationInput, EngineConfig
    from memory_manager import MemoryManager

    event_id = uuid.uuid4().hex[:12]
    query = f"[来源: {post['source']}] {post['title']}"

    try:
        # 生成标题
        title = await generate_title(query[:500])

        # 引擎配置
        config = EngineConfig(model=MODEL, temperature=0.7, max_tokens=2048, api_key=API_KEY, base_url=BASE_URL)
        mem = MemoryManager(
            user_id=f"mine_{event_id}",
            openai_api_key=API_KEY, openai_base_url=BASE_URL,
            storage_dir=os.path.join(os.path.dirname(__file__), "..", "data", "memory"),
        )
        engine = CognitiveEngine(config=config, memory_manager=mem)
        user_input = SimulationInput(user_id=f"mine_{event_id}", text=query[:500])

        full_text = ""
        t0 = time.time()
        async for data in engine.simulate_stream(user_input):
            if data.startswith("data: "):
                try:
                    payload = json.loads(data[6:])
                    if payload.get("type") == "content":
                        full_text += payload.get("text", "")
                except json.JSONDecodeError:
                    pass

        if not full_text.strip():
            return None

        elapsed_ms = int((time.time() - t0) * 1000)
        topology = parse_topology(full_text)

        # 保存到 SQLite
        conn = get_db()
        conn.execute(
            """INSERT INTO public_events (id, title, query, result, mode, topology_json, stats_json, created_at, ip_hash, anonymous_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id, title, query[:500], full_text, "v4",
                json.dumps(topology, ensure_ascii=False) if topology else None,
                json.dumps({"length": len(full_text), "elapsed_ms": elapsed_ms, "source": post["source"]}, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
                "auto_miner", "auto_miner",
            ),
        )
        conn.commit()
        conn.close()

        return event_id
    except Exception:
        return None


# ═══════════════════════════════════════════
# 主管道入口
# ═══════════════════════════════════════════

async def run_mining_pipeline(max_per_source: int = 10) -> dict:
    """
    执行完整采集管道：
    1. 从各平台采集帖子
    2. LLM 筛选个人决策
    3. 自动推演入库

    返回统计信息
    """
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    stats = {
        "sources": {},
        "total_fetched": 0,
        "total_decisions": 0,
        "total_deduced": 0,
        "new_events": [],
    }

    # ── 1. 采集 Reddit ──
    for source_key, source_info in SOURCES.items():
        source_name = source_info["name"]
        posts = []

        if source_info["type"] == "json":
            for url in source_info["urls"]:
                if "reddit" in source_key:
                    posts.extend(await fetch_reddit_posts(url))
                elif source_key == "v2ex":
                    posts.extend(await fetch_v2ex_posts())

        # 去重
        seen = set()
        unique_posts = []
        for p in posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique_posts.append(p)

        stats["sources"][source_name] = {"fetched": len(unique_posts), "decisions": 0, "deduced": 0}
        stats["total_fetched"] += len(unique_posts)

        # ── 2. 筛选（限速：每秒1条）──
        decisions = []
        for i, post in enumerate(unique_posts[:max_per_source]):
            is_decision = await classify_decision(client, post["title"], post["content"])
            if is_decision:
                decisions.append(post)
            if i % 3 == 0:
                await asyncio.sleep(0.3)  # 速率控制

        stats["sources"][source_name]["decisions"] = len(decisions)
        stats["total_decisions"] += len(decisions)

        # ── 3. 自动推演（限速：每2秒1条）──
        for j, post in enumerate(decisions[:max_per_source]):
            event_id = await auto_deduce_and_save(client, post)
            if event_id:
                stats["sources"][source_name]["deduced"] += 1
                stats["total_deduced"] += 1
                stats["new_events"].append({
                    "id": event_id,
                    "title": post["title"],
                    "source": post["source"],
                })
            if j < len(decisions) - 1:
                await asyncio.sleep(2)  # API速率限制

    return stats
