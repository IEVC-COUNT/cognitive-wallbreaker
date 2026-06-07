"""
认知破壁机 V6.0 — 公共推演平台 API
POST /api/public/submit       — 提交决策 + 推演 + 入库
GET  /api/public/events        — 事件列表（分页+排序）
GET  /api/public/events/{id}   — 事件详情（含现实反馈）
POST /api/public/events/{id}/outcome — 提交现实结果反馈
"""
import json
import uuid
import hashlib
import asyncio
import re
import os
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI

from database import get_db
from engine import CognitiveEngine, SimulationInput, EngineConfig

router = APIRouter(prefix="/api/public")

# 复用 main.py 的配置
API_KEY = os.getenv("OPENAI_API_KEY", "sk-39d2be9a198742978eb9cabc3cc5bf05")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:4000/v1")
MODEL = os.getenv("WALLBREAKER_MODEL", "deepseek-v4-flash")


# ═══════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════

async def generate_title(query: str) -> str:
    """用 LLM 从 query 生成 15-20 字的中文标题"""
    try:
        client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=MODEL, temperature=0.3, max_tokens=40,
                messages=[{"role": "user", "content": f"将以下决策问题概括为15-20字以内的精炼中文标题，只输出标题：\n{query[:500]}"}],
            ), timeout=15,
        )
        title = resp.choices[0].message.content.strip()
        return title[:40]
    except Exception:
        return query[:20] + ("..." if len(query) > 20 else "")


def parse_topology(text: str) -> Optional[dict]:
    """从推演文本中提取拓扑 JSON"""
    if not text:
        return None
    json_pattern = r'```json\s*\n(.*?)\n\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)
    if not matches:
        json_pattern = r'```\s*\n(\{[\s\S]*?\})\s*\n\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
    if not matches:
        json_pattern = r'\{[\s\S]*"topology_version"[\s\S]*"nodes"[\s\S]*"edges"[\s\S]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        cleaned = match.strip()
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        cleaned = re.sub(r'//[^\n]*', '', cleaned)
        cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if "nodes" not in data or "edges" not in data:
            continue
        if len(data["nodes"]) < 3:
            continue
        return data
    return None


def load_anonymous_memory(anonymous_id: str) -> dict:
    """加载匿名用户的累积记忆"""
    if not anonymous_id:
        return {"events": [], "profile": ""}
    conn = get_db()
    row = conn.execute("SELECT memory_json FROM anonymous_memory WHERE anonymous_id = ?", (anonymous_id,)).fetchone()
    conn.close()
    if row and row["memory_json"]:
        try:
            return json.loads(row["memory_json"])
        except json.JSONDecodeError:
            pass
    return {"events": [], "profile": ""}


def save_anonymous_memory(anonymous_id: str, memory: dict):
    """保存匿名用户的累积记忆"""
    if not anonymous_id:
        return
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute("SELECT event_count FROM anonymous_memory WHERE anonymous_id = ?", (anonymous_id,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE anonymous_memory SET memory_json = ?, event_count = event_count + 1, updated_at = ? WHERE anonymous_id = ?",
            (json.dumps(memory, ensure_ascii=False), now, anonymous_id),
        )
    else:
        conn.execute(
            "INSERT INTO anonymous_memory (anonymous_id, memory_json, event_count, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
            (anonymous_id, json.dumps(memory, ensure_ascii=False), now, now),
        )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════

@router.post("/submit")
async def public_submit(
    request: Request,
    event: str = Form(default=""),
    mode: str = Form(default="v4"),
    anonymous_id: str = Form(default=""),
    images: Optional[List[UploadFile]] = File(default=None),
):
    """
    提交公共推演事件，SSE 流式返回推演结果。
    支持 anonymous_id 跨会话记忆累积。

    参数:
      event: 决策描述文本
      mode: v4 | v5 | dual
      anonymous_id: 匿名用户标识（前端 localStorage 维护）
      images: 可选图片（最多5张）
    """
    if not event.strip():
        async def err():
            yield f"data: {json.dumps({'type': 'error', 'text': '请输入决策描述'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    # 事件 ID + 匿名标识
    event_id = uuid.uuid4().hex[:12]
    ip_hash = hashlib.sha256(
        (request.client.host if request.client else "127.0.0.1").encode()
    ).hexdigest()[:16]

    # 加载匿名用户记忆
    anon_memory = load_anonymous_memory(anonymous_id)
    memory_context = ""
    past_events = anon_memory.get("events", [])
    if past_events:
        memory_context = "## 该用户的历史决策记录\n"
        for pe in past_events[-5:]:  # 最近5条
            memory_context += f"- 决策: {pe.get('query','')[:100]}\n  结果概要: {pe.get('summary','')[:150]}\n"

    # 生成标题（并行）
    title_task = asyncio.create_task(generate_title(event.strip()))

    # 构建增强的输入（含记忆上下文）
    enhanced_text = event.strip()
    if memory_context:
        enhanced_text = f"{memory_context}\n\n---\n\n## 当前决策\n{event.strip()}\n\n请结合用户的历史决策模式进行分析。"

    # 使用 V4 引擎
    engine_config = EngineConfig(
        model=MODEL, temperature=0.7, max_tokens=2560,
        api_key=API_KEY, base_url=BASE_URL,
    )
    from memory_manager import MemoryManager
    synthetic_uid = f"pub_{event_id}"
    mem = MemoryManager(
        user_id=synthetic_uid,
        openai_api_key=API_KEY, openai_base_url=BASE_URL,
        storage_dir=os.path.join(os.path.dirname(__file__), "..", "data", "memory"),
    )
    engine = CognitiveEngine(config=engine_config, memory_manager=mem)
    user_input = SimulationInput(user_id=synthetic_uid, text=enhanced_text)

    async def event_stream():
        full_text = ""
        start_time = None
        import time
        start_time = time.time()

        try:
            async for data in engine.simulate_stream(user_input):
                if await request.is_disconnected():
                    break
                if data.startswith("data: "):
                    try:
                        payload = json.loads(data[6:])
                        if payload.get("type") == "content":
                            full_text += payload.get("text", "")
                    except json.JSONDecodeError:
                        pass
                yield data

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 提取拓扑
            topology = None
            if full_text.strip():
                topology = parse_topology(full_text)

            # 生成结果概要（用于记忆）
            result_summary = full_text[:300] if full_text else ""

            # 获取标题
            title = await title_task

            # 更新匿名记忆
            if anonymous_id:
                past_events.append({
                    "query": event.strip()[:200],
                    "summary": result_summary,
                    "mode": mode,
                    "time": datetime.now(timezone.utc).isoformat(),
                })
                if len(past_events) > 20:  # 最多保留20条
                    past_events = past_events[-20:]
                anon_memory["events"] = past_events
                try:
                    save_anonymous_memory(anonymous_id, anon_memory)
                except Exception:
                    pass

            # 保存到 SQLite
            try:
                conn = get_db()
                conn.execute(
                    """INSERT INTO public_events (id, title, query, result, mode, topology_json, stats_json, created_at, ip_hash, anonymous_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event_id, title, event.strip()[:500], full_text, mode,
                        json.dumps(topology, ensure_ascii=False) if topology else None,
                        json.dumps({"length": len(full_text), "elapsed_ms": elapsed_ms}, ensure_ascii=False),
                        datetime.now(timezone.utc).isoformat(),
                        ip_hash, anonymous_id[:32],
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'text': f'保存失败: {str(e)[:200]}'})}\n\n"
                return

            # 完成事件
            yield f"data: {json.dumps({'type': 'done', 'length': len(full_text), 'elapsed_ms': elapsed_ms, 'event_id': event_id, 'mode': mode}, ensure_ascii=False)}\n\n"

            if topology:
                yield f"data: {json.dumps({'type': 'topology', 'data': topology}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': f'引擎异常: {str(e)[:200]}'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/events")
async def list_events(page: int = 1, size: int = 20, sort: str = "recent"):
    """获取公共事件列表（分页+排序）"""
    size = min(size, 50)
    offset = (page - 1) * size
    order = "created_at DESC" if sort == "recent" else "view_count DESC"

    conn = get_db()
    rows = conn.execute(
        f"""SELECT id, title, query, mode, stats_json, topology_json, created_at, view_count, like_count
            FROM public_events ORDER BY {order} LIMIT ? OFFSET ?""",
        (size, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM public_events").fetchone()[0]
    conn.close()

    events = []
    for r in rows:
        stats = json.loads(r["stats_json"]) if r["stats_json"] else {}
        has_topo = r["topology_json"] is not None and len(r["topology_json"] or "") > 10
        events.append({
            "id": r["id"],
            "title": r["title"],
            "query_preview": (r["query"] or "")[:200],
            "mode": r["mode"],
            "stats": stats,
            "has_topology": has_topo,
            "created_at": r["created_at"],
            "view_count": r["view_count"],
            "like_count": r["like_count"],
        })

    return {"events": events, "total": total, "page": page, "size": size}


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """获取单条公共事件详情（含现实反馈）"""
    conn = get_db()
    row = conn.execute("SELECT * FROM public_events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "事件不存在"})

    # 增加浏览量
    conn.execute("UPDATE public_events SET view_count = view_count + 1 WHERE id = ?", (event_id,))

    # 获取现实反馈
    outcomes = conn.execute(
        "SELECT * FROM event_outcomes WHERE event_id = ? ORDER BY created_at DESC", (event_id,)
    ).fetchall()
    conn.commit()
    conn.close()

    return {
        "id": row["id"],
        "title": row["title"],
        "query": row["query"],
        "result": row["result"],
        "mode": row["mode"],
        "topology": json.loads(row["topology_json"]) if row["topology_json"] else None,
        "stats": json.loads(row["stats_json"]) if row["stats_json"] else {},
        "created_at": row["created_at"],
        "view_count": row["view_count"] + 1,
        "like_count": row["like_count"],
        "outcomes": [{
            "id": o["id"],
            "outcome_text": o["outcome_text"],
            "accuracy_score": o["accuracy_score"],
            "created_at": o["created_at"],
        } for o in outcomes],
    }


@router.post("/events/{event_id}/outcome")
async def add_outcome(
    event_id: str,
    outcome_text: str = Form(default=""),
    accuracy_score: int = Form(default=3),
):
    """提交现实结果反馈 — 用户标记决策的真实结果"""
    if not outcome_text.strip():
        return JSONResponse(status_code=400, content={"error": "请填写现实结果"})

    score = max(1, min(5, accuracy_score))

    conn = get_db()
    # 验证事件存在
    row = conn.execute("SELECT id FROM public_events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return JSONResponse(status_code=404, content={"error": "事件不存在"})

    conn.execute(
        "INSERT INTO event_outcomes (event_id, outcome_text, accuracy_score, created_at) VALUES (?, ?, ?, ?)",
        (event_id, outcome_text.strip()[:2000], score, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "message": "现实反馈已提交"}
