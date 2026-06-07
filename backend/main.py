"""
认知破壁机 V6.0 — FastAPI 后端
公共个人决策推演平台 + 多智能体对抗 + SSE流式 + 拓扑沙盘
"""
import json
import asyncio
import base64
import re
import os
from pathlib import Path

# 自动加载项目根目录的 .env 配置
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path, override=True)
except ImportError:
    pass

from typing import Optional, List
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI

from engine import (
    CognitiveEngine,
    SimulationInput,
    EngineConfig,
    encode_image_bytes_to_base64,
    get_image_mime_type,
)
from engine_v5 import (
    V5CognitiveEngine,
    V5FastEngine,
    V5SimulationInput,
    V5EngineConfig,
)
from memory_manager import MemoryManager
from history_manager import HistoryManager

# ═══════════════════════════════════════════
# 拓扑 JSON 解析器
# ═══════════════════════════════════════════

def parse_topology_v2(text: str) -> Optional[dict]:
    """
    从大模型输出中提取并验证拓扑沙盘 JSON 数据

    V4.0 核心特性：大模型在文本推演后输出 topology JSON。
    此函数负责：
    1. 从文本中提取 ```json ... ``` 代码块
    2. 验证 JSON 结构和必需字段
    3. 如果 AI 输出格式错误（如多余的逗号、注释），尝试修复
    4. 失败时返回 None，让前端优雅降级为纯文本模式

    Args:
        text: 大模型完整输出文本

    Returns:
        合法的 topology dict，或 None
    """
    if not text:
        return None

    # 1. 提取 JSON 代码块（```json ... ```）
    json_pattern = r'```json\s*\n(.*?)\n\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)

    if not matches:
        # 尝试匹配没有语言标记的代码块
        json_pattern = r'```\s*\n(\{[\s\S]*?\})\s*\n\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)

    if not matches:
        # 最后一次尝试：直接找 JSON 对象
        json_pattern = r'\{[\s\S]*"topology_version"[\s\S]*"nodes"[\s\S]*"edges"[\s\S]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

    for match in matches:
        # 2. 尝试解析
        cleaned = match.strip()

        # 移除可能的尾部逗号（AI 常见错误）
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)

        # 移除 JSON 内部的 // 和 /* */ 注释（AI 违规行为）
        cleaned = re.sub(r'//[^\n]*', '', cleaned)
        cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            continue

        # 3. 验证结构
        if not isinstance(data, dict):
            continue

        if "nodes" not in data or "edges" not in data:
            continue

        if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
            continue

        # 4. 验证并修复节点
        valid_types = {"core", "risk", "safe", "social", "psychology", "future"}
        valid_nodes = []
        for node in data["nodes"]:
            if not isinstance(node, dict):
                continue
            if "id" not in node or "label" not in node:
                continue
            # 标准化 type 字段
            if node.get("type") not in valid_types:
                node["type"] = "core"
            valid_nodes.append(node)

        # 5. 验证 edges 引用合法性
        node_ids = {n["id"] for n in valid_nodes}
        valid_edges = []
        for edge in data["edges"]:
            if not isinstance(edge, dict):
                continue
            if "source" not in edge or "target" not in edge:
                continue
            # 只保留引用存在的 edges
            if edge["source"] in node_ids and edge["target"] in node_ids:
                valid_edges.append(edge)

        if len(valid_nodes) < 3:
            continue  # 节点太少，不值得渲染

        return {
            "topology_version": data.get("topology_version", "2.0"),
            "nodes": valid_nodes,
            "edges": valid_edges,
        }

    return None


# ═══════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════

app = FastAPI(
    title="认知破壁机 · 公共个人决策推演平台",
    version="6.0.0",
    description="AI多智能体对抗推演 — 七Agent辩论，魔鬼代言人挑刺，终审法官判决",
)

# 初始化 SQLite 公共事件数据库
from database import init_db
init_db()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Elapsed-Time"],
)

# ═══════════════════════════════════════════
# 全局引擎实例
# ═══════════════════════════════════════════

# 从环境变量读取配置
API_KEY = os.getenv("OPENAI_API_KEY", "sk-39d2be9a198742978eb9cabc3cc5bf05")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:4000/v1")
MODEL = os.getenv("WALLBREAKER_MODEL", "deepseek-v4-flash")

# ── V4.0 引擎配置（保留兼容）──
engine_config = EngineConfig(
    model=MODEL,
    temperature=0.7,
    max_tokens=4096,
    api_key=API_KEY,
    base_url=BASE_URL,
)

# ── V5 多智能体引擎配置（V6.0 保留兼容）──
v5_engine_config = V5EngineConfig(
    model=MODEL,
    api_key=API_KEY,
    base_url=BASE_URL,
    agent_timeout=float(os.getenv("V5_AGENT_TIMEOUT", "45")),
)

# 内存记忆管理器（每个 user_id 独立）
memory_managers: dict[str, MemoryManager] = {}

# 历史记录管理器（每个 user_id 独立）
history_managers: dict[str, HistoryManager] = {}


def get_memory_manager(user_id: str) -> MemoryManager:
    """获取或创建用户的记忆管理器"""
    if user_id not in memory_managers:
        memory_managers[user_id] = MemoryManager(
            user_id=user_id,
            openai_api_key=API_KEY,
            openai_base_url=BASE_URL,
            storage_dir=os.path.join(os.path.dirname(__file__), "..", "data", "memory"),
        )
    return memory_managers[user_id]


def get_history_manager(user_id: str) -> HistoryManager:
    """获取或创建用户的历史记录管理器"""
    if user_id not in history_managers:
        history_managers[user_id] = HistoryManager(
            user_id=user_id,
            storage_dir=os.path.join(os.path.dirname(__file__), "..", "data", "history"),
        )
    return history_managers[user_id]


def get_engine(user_id: str) -> CognitiveEngine:
    """获取用户的推演引擎实例"""
    return CognitiveEngine(
        config=engine_config,
        memory_manager=get_memory_manager(user_id),
    )


# ═══════════════════════════════════════════
# 图片处理辅助函数
# ═══════════════════════════════════════════

async def process_uploaded_images(
    files: Optional[List[UploadFile]],
) -> List[str]:
    """
    处理上传的图片文件，转换为 Base64 列表

    Args:
        files: UploadFile 列表

    Returns:
        Base64 编码的图片字符串列表（不含 data URI 前缀）
    """
    if not files:
        return []

    images_base64 = []

    for upload_file in files:
        # 读取文件内容
        content = await upload_file.read()

        # 跳过空文件
        if not content:
            continue

        # 检测 MIME 类型
        mime_type = get_image_mime_type(content)

        # 编码为 Base64
        img_b64 = encode_image_bytes_to_base64(content)

        # 存储完整的 data URI，方便直接传给 OpenAI Vision
        img_uri = f"data:{mime_type};base64,{img_b64}"
        images_base64.append(img_uri)

    return images_base64


async def process_single_image(file: UploadFile) -> Optional[str]:
    """处理单个图片上传，返回 Base64 data URI"""
    if not file:
        return None

    content = await file.read()
    if not content:
        return None

    mime_type = get_image_mime_type(content)
    img_b64 = encode_image_bytes_to_base64(content)
    return f"data:{mime_type};base64,{img_b64}"


# ═══════════════════════════════════════════
# API 接口
# ═══════════════════════════════════════════

@app.post("/api/simulate")
async def simulate(
    request: Request,
    event: str = Form(default="", description="用户输入的决策事件文本"),
    user_id: str = Form(default="default", description="用户标识，用于记忆隔离"),
    images: Optional[List[UploadFile]] = File(default=None, description="上传的图片（可选，最多5张）"),
):
    """
    认知破壁机推演接口

    支持 multipart/form-data 格式，同时接收文本和图片。
    返回 SSE (text/event-stream) 流式响应。

    请求示例（curl）:
      curl -X POST http://localhost:8900/api/simulate \
        -F "event=要不要跳槽去创业公司" \
        -F "user_id=user_001" \
        -F "images=@screenshot.png"

    事件类型:
      - thinking:  引擎思考中（含进度提示）
      - content_start: 开始输出推演内容
      - content:   推演内容增量文本
      - done:      推演完成
      - error:     错误信息
    """

    # 1. 验证输入
    if not event.strip() and (not images or len(images) == 0):
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'text': '请至少提供文本描述或图片'})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    # 2. 限制图片数量
    if images:
        images = images[:5]  # 最多 5 张

    # 3. 处理图片
    images_base64 = await process_uploaded_images(images)

    # 4. 构建输入
    user_input = SimulationInput(
        user_id=user_id,
        text=event.strip(),
        images_base64=images_base64 if images_base64 else None,
    )

    # 5. 获取引擎实例
    engine = get_engine(user_id)

    # 6. 返回 SSE 流式响应（含拓扑沙盘数据）
    async def event_stream():
        full_text = ""
        topology_sent = False
        final_stats = {}

        async for data in engine.simulate_stream(user_input):
            if await request.is_disconnected():
                break

            # 收集完整文本用于拓扑解析
            if data.startswith("data: "):
                try:
                    payload = json.loads(data[6:])
                    if payload.get("type") == "content":
                        full_text += payload.get("text", "")
                    if payload.get("type") == "done":
                        final_stats = {
                            "length": payload.get("length", len(full_text)),
                            "elapsed_ms": payload.get("elapsed_ms", 0),
                        }
                        # 推演完成 → 解析拓扑沙盘 JSON
                        if not topology_sent:
                            topology = parse_topology_v2(full_text)
                            if topology:
                                yield f"data: {json.dumps({'type': 'topology', 'data': topology}, ensure_ascii=False)}\n\n"
                            topology_sent = True
                except json.JSONDecodeError:
                    pass

            yield data
            await asyncio.sleep(0.001)

        # 兜底：如果 done 事件没触发 topology
        topology = None
        if not topology_sent:
            topology = parse_topology_v2(full_text)
            if topology:
                yield f"data: {json.dumps({'type': 'topology', 'data': topology}, ensure_ascii=False)}\n\n"

        # 💾 自动保存历史记录
        if full_text.strip():
            if topology is None:
                topology = parse_topology_v2(full_text)
            try:
                history = get_history_manager(user_id)
                record_id = history.save(
                    query=event.strip(),
                    result=full_text,
                    topology=topology,
                    stats=final_stats if final_stats else {"length": len(full_text), "elapsed_ms": 0},
                    images_count=len(images_base64) if images_base64 else 0,
                )
                yield f"data: {json.dumps({'type': 'history_saved', 'record_id': record_id}, ensure_ascii=False)}\n\n"
            except Exception:
                pass  # 历史保存失败不中断推演

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


@app.post("/api/simulate/json")
async def simulate_json(
    request: Request,
    event: str = Form(default=""),
    user_id: str = Form(default="default"),
    images: Optional[List[UploadFile]] = File(default=None),
):
    """
    非流式接口 — 等待完整结果后返回 JSON

    适用于需要一次性获取结果的场景。
    """
    if not event.strip() and (not images or len(images) == 0):
        return JSONResponse(
            status_code=400,
            content={"error": "请至少提供文本描述或图片"},
        )

    if images:
        images = images[:5]

    images_base64 = await process_uploaded_images(images)

    user_input = SimulationInput(
        user_id=user_id,
        text=event.strip(),
        images_base64=images_base64 if images_base64 else None,
    )

    engine = get_engine(user_id)

    full_text = ""
    async for data in engine.simulate_stream(user_input):
        if await request.is_disconnected():
            break
        if data.startswith("data: "):
            try:
                payload = json.loads(data[6:])
                if payload.get("type") == "content":
                    full_text += payload.get("text", "")
            except json.JSONDecodeError:
                continue

    return {
        "result": full_text,
        "length": len(full_text),
        "user_id": user_id,
        "has_images": bool(images_base64),
    }


@app.get("/api/health")
async def health():
    """健康检查接口"""
    return {
        "status": "ok",
        "service": "Cognitive Wallbreaker v6.0",
        "version": "6.0.0",
        "model": MODEL,
        "base_url": BASE_URL,
        "endpoints": {
            "v4": "/api/simulate",
            "v4_json": "/api/simulate/json",
            "v5_full": "/api/simulate/v5",
            "v5_fast": "/api/simulate/v5/fast",
            "dual": "/api/simulate/dual",
        },
        "agents": {
            "full": ["psychology", "interest", "class", "game", "soul", "devil", "judge"],
            "fast": ["psychology", "interest", "judge"],
        },
    }


@app.get("/api/memory/stats")
async def memory_stats(user_id: str = "default"):
    """获取用户记忆统计"""
    mem = get_memory_manager(user_id)
    return mem.stats()


@app.post("/api/memory/clear")
async def clear_memory(user_id: str = Form(default="default")):
    """清除用户记忆"""
    mem = get_memory_manager(user_id)
    mem.clear_user_memories()
    return {"status": "ok", "message": f"用户 {user_id} 的记忆已清除"}


@app.get("/api/memory/list")
async def list_memories(user_id: str = "default", limit: int = 20):
    """列出用户的记忆"""
    mem = get_memory_manager(user_id)
    memories = mem.search("", limit=limit)
    return {
        "user_id": user_id,
        "total": len(mem._local_memories),
        "memories": memories,
    }


# ═══════════════════════════════════════════
# 历史记录接口
# ═══════════════════════════════════════════

@app.get("/api/history/list")
async def list_history(user_id: str = "default", limit: int = 50):
    """列出用户的历史推演记录（摘要）"""
    history = get_history_manager(user_id)
    records = history.list(limit=limit)
    return {
        "user_id": user_id,
        "total": len(records),
        "records": records,
    }


@app.get("/api/history/stats")
async def history_stats(user_id: str = "default"):
    """历史记录统计"""
    history = get_history_manager(user_id)
    return history.stats()


@app.get("/api/history/{record_id}")
async def get_history(record_id: str, user_id: str = "default"):
    """获取单条完整推演记录"""
    history = get_history_manager(user_id)
    record = history.get(record_id)
    if record is None:
        return JSONResponse(status_code=404, content={"error": "记录不存在"})
    return record


@app.delete("/api/history/{record_id}")
async def delete_history(record_id: str, user_id: str = "default"):
    """删除一条推演记录"""
    history = get_history_manager(user_id)
    ok = history.delete(record_id)
    if not ok:
        return JSONResponse(status_code=404, content={"error": "记录不存在"})
    return {"status": "ok", "deleted": record_id}


# ═══════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════

def get_v5_engine(user_id: str) -> V5CognitiveEngine:
    """获取用户的 V5 多智能体推演引擎"""
    return V5CognitiveEngine(
        config=v5_engine_config,
        memory_manager=get_memory_manager(user_id),
    )


def get_v5_fast_engine(user_id: str) -> V5FastEngine:
    """获取用户的 V5 快速模式引擎（3 Agent）"""
    return V5FastEngine(
        config=v5_engine_config,
        memory_manager=get_memory_manager(user_id),
    )


# ═══════════════════════════════════════════
# V5.0 API: 多智能体对抗推演 (7 Agent)
# ═══════════════════════════════════════════

@app.post("/api/simulate/v5")
async def simulate_v5(
    request: Request,
    event: str = Form(default="", description="用户输入的决策事件文本"),
    user_id: str = Form(default="default", description="用户标识"),
    images: Optional[List[UploadFile]] = File(default=None),
):
    """
    V5.0 多智能体对抗推演接口（7 Agent 完整版）

    推演流程：
      Agent 1-3 并行：心理刀 + 利益刀 + 阶层刀
      Agent 4-5 串行：博弈刀 → 灵魂刀
      Agent 6：魔鬼代言人逐刀反驳
      Agent 7：首席推演官终审判决 + 拓扑沙盘

    SSE 事件类型：
      - phase:         阶段切换
      - agent_done:    单个 Agent 完成（含完整输出文本）
      - agent_error:   单个 Agent 异常
      - topology:      拓扑沙盘 JSON
      - done:          全部完成
      - error:         引擎级错误
    """
    if not event.strip() and (not images or len(images) == 0):
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'text': '请至少提供文本描述或图片'})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    if images:
        images = images[:5]

    # 处理图片（复用 V4.0 OCR 方式）
    images_base64 = await process_uploaded_images(images)

    # 构建增强文本（图片OCR注入）
    enhanced_text = event.strip()
    if images_base64:
        ocr_texts = []
        for img_b64 in images_base64:
            ocr_result = _ocr_single_image(img_b64)
            if ocr_result:
                ocr_texts.append(ocr_result)
        if ocr_texts:
            ocr_block = "\n\n---\n📷 **图片OCR识别内容**：\n"
            for i, t in enumerate(ocr_texts):
                ocr_block += f"\n[图片{i+1}]:\n{t}\n"
            ocr_block += "\n请结合以上图片中的文字信息进行分析。\n---"
            enhanced_text += ocr_block

    user_input = V5SimulationInput(
        user_id=user_id,
        text=enhanced_text if enhanced_text else "请分析这张图片",
        images_base64=images_base64 if images_base64 else None,
    )

    engine = get_v5_engine(user_id)

    async def event_stream():
        full_text_parts = []

        async for data in engine.simulate_stream(user_input):
            if await request.is_disconnected():
                break

            # 收集各 Agent 输出用于历史保存
            if data.startswith("data: "):
                try:
                    payload = json.loads(data[6:])
                    if payload.get("type") == "agent_done":
                        full_text_parts.append({
                            "agent": payload.get("agent"),
                            "name": payload.get("name"),
                            "text": payload.get("text", ""),
                        })
                except json.JSONDecodeError:
                    pass

            yield data
            await asyncio.sleep(0.001)

        # 💾 保存历史
        if full_text_parts:
            try:
                history = get_history_manager(user_id)
                merged = "\n\n---\n\n".join([
                    f"## {p['name']}\n{p['text']}" for p in full_text_parts
                ])
                history.save(
                    query=event.strip(),
                    result=merged,
                    topology=None,
                    stats={
                        "version": "5.0",
                        "agents_count": len(full_text_parts),
                    },
                )
            except Exception:
                pass

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


# ═══════════════════════════════════════════
# V5.0 快速模式: 3 Agent 降级版
# ═══════════════════════════════════════════

@app.post("/api/simulate/v5/fast")
async def simulate_v5_fast(
    request: Request,
    event: str = Form(default=""),
    user_id: str = Form(default="default"),
    images: Optional[List[UploadFile]] = File(default=None),
):
    """
    V5.0 快速模式（3 Agent）

    推演流程：
      心理刀 + 利益刀 并行 → 法官（兼任博弈+灵魂+魔鬼职责）

    适合需要快速结果的场景，成本约为完整版的 40%。
    """
    if not event.strip() and (not images or len(images) == 0):
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'text': '请至少提供文本描述或图片'})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    if images:
        images = images[:5]

    images_base64 = await process_uploaded_images(images)

    enhanced_text = event.strip()
    if images_base64:
        ocr_texts = []
        for img_b64 in images_base64:
            ocr_result = _ocr_single_image(img_b64)
            if ocr_result:
                ocr_texts.append(ocr_result)
        if ocr_texts:
            ocr_block = "\n\n---\n📷 **图片OCR识别内容**：\n"
            for i, t in enumerate(ocr_texts):
                ocr_block += f"\n[图片{i+1}]:\n{t}\n"
            ocr_block += "\n请结合以上图片中的文字信息进行分析。\n---"
            enhanced_text += ocr_block

    user_input = V5SimulationInput(
        user_id=user_id,
        text=enhanced_text if enhanced_text else "请分析这张图片",
        images_base64=images_base64 if images_base64 else None,
    )

    engine = get_v5_fast_engine(user_id)

    async def event_stream():
        full_text_parts = []

        async for data in engine.simulate_stream(user_input):
            if await request.is_disconnected():
                break
            if data.startswith("data: "):
                try:
                    payload = json.loads(data[6:])
                    if payload.get("type") == "agent_done":
                        full_text_parts.append({
                            "agent": payload.get("agent"),
                            "name": payload.get("name"),
                            "text": payload.get("text", ""),
                        })
                except json.JSONDecodeError:
                    pass
            yield data
            await asyncio.sleep(0.001)

        if full_text_parts:
            try:
                history = get_history_manager(user_id)
                merged = "\n\n---\n\n".join([
                    f"## {p['name']}\n{p['text']}" for p in full_text_parts
                ])
                history.save(
                    query=event.strip(),
                    result=merged,
                    topology=None,
                    stats={
                        "version": "5.0-fast",
                        "agents_count": len(full_text_parts),
                    },
                )
            except Exception:
                pass

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


# ═══════════════════════════════════════════
# V5.0 双路推演: 乐观路径 vs 悲观路径
# ═══════════════════════════════════════════

# 双路推演专用 System Prompt 模板
DUAL_PATH_SYSTEM_TEMPLATE = """# Role: 认知破壁机 V5.0 - 双路对比推演引擎

你是"认知破壁机"推演引擎。你的任务是对用户的决策进行深度分析。

{path_instruction}

# 当前用户档案
{memory_context}

# Core Workflow (五刀推演 + 拓扑沙盘):

## Part 1: 文本解剖 (五刀推演)

### 🔪 第一刀：心理防御与认知盲区（内因）
- 用户正在使用的心理防御机制
- 至少 3 个"自我欺骗"信号
> 💀 破壁人点评：[20字]

### 🔪 第二刀：利益链条与收割逻辑（外因）
- 谁是庄家？谁在割韭菜？
- 具体利益流向说明
> 💀 破壁人点评：[20字]

### 🔪 第三刀：阶层筹码与容错率计算（现实）
- 底线压力测试，量化毁灭性打击
> 💀 破壁人点评：[20字]

### 🔪 第四刀：灰度博弈与反向操作（行动）
- 2 条具体可执行的博弈策略
> 💀 破壁人点评：[20字]

### 🔪 第五刀：终极破壁拷问（灵魂暴击）
- 一个直击社会现实与个人命运的问题
> 💀 破壁人点评：[20字]

---

## Part 2: 拓扑沙盘数据

你必须输出一个合法的 JSON 代码块。

```json
{{
  "topology_version": "2.0",
  "nodes": [
    {{ "id": "n1", "label": "核心决策", "type": "core", "description": "当前核心决策" }},
    {{ "id": "n2", "label": "风险分支", "type": "risk", "description": "高危后果" }},
    {{ "id": "n3", "label": "安全路径", "type": "safe", "description": "可行策略" }}
  ],
  "edges": [
    {{ "source": "n1", "target": "n2", "label": "导致" }},
    {{ "source": "n1", "target": "n3", "label": "博弈出口" }}
  ]
}}
```

节点类型: core/risk/safe/social/psychology/future，总数不少于8个节点。
JSON 必须合法，禁止注释，禁止多余逗号。用中文输出，1500-2500字。"""

DUAL_PATH_A_INSTRUCTION = """**本路径视角：乐观/积极路径 (Path A)**
你需要在分析中找到决策中的**机会窗口**和**潜在上升空间**。
虽然保持冷静和现实，但请重点指出：
1. 如果成功，最大的收益是什么
2. 有哪些被用户忽略的积极因素
3. 社会/行业趋势中有利于此决策的信号
4. 博弈策略重点放在"如何提高成功概率"
5. 灵魂拷问侧重"如果不做会后悔什么"
在拓扑沙盘中，至少包含 2 个 "future" 类型的正面衍生节点。"""

DUAL_PATH_B_INSTRUCTION = """**本路径视角：悲观/防御路径 (Path B)**
你需要在分析中重点揭示决策中的**毁灭性风险**和**隐藏陷阱**。
保持极度冷峻，请重点指出：
1. 最坏情况下的具体损失（量化）
2. 有哪些被用户忽视的危险信号
3. 社会/行业趋势中不利于此决策的信号
4. 博弈策略重点放在"如何止损和退出"
5. 灵魂拷问侧重"你输得起吗"
在拓扑沙盘中，至少包含 2 个 "risk" 类型的高危节点。"""


@app.post("/api/simulate/dual")
async def simulate_dual(
    request: Request,
    event: str = Form(default="", description="用户输入的决策事件文本"),
    user_id: str = Form(default="default", description="用户标识"),
    images: Optional[List[UploadFile]] = File(default=None),
):
    """
    V5.0 双路对比推演 — 乐观路径 vs 悲观路径并行推演

    两条路径使用不同的视角同时分析同一决策，结果以 SSE 流式返回。
    每条路径独立输出文本内容和拓扑沙盘。

    SSE 事件类型：
      - meta:          元信息（路径标签）
      - content:       推演内容增量（含 path 标识 a/b）
      - topology:      拓扑沙盘数据（含 path 标识 a/b）
      - done:          单路径完成（含 path 标识 a/b）
      - error:         单路径错误（含 path 标识 a/b）
    """
    if not event.strip() and (not images or len(images) == 0):
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'text': '请至少提供文本描述或图片'})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    if images:
        images = images[:5]

    images_base64 = await process_uploaded_images(images)

    # 处理 OCR
    enhanced_text = event.strip()
    if images_base64:
        ocr_texts = []
        for img_b64 in images_base64:
            ocr_result = _ocr_single_image(img_b64)
            if ocr_result:
                ocr_texts.append(ocr_result)
        if ocr_texts:
            ocr_block = "\n\n---\n📷 **图片OCR识别内容**：\n"
            for i, t in enumerate(ocr_texts):
                ocr_block += f"\n[图片{i+1}]:\n{t}\n"
            ocr_block += "\n请结合以上图片中的文字信息进行分析。\n---"
            enhanced_text += ocr_block

    if not enhanced_text.strip():
        enhanced_text = "请分析我当前面临的决策困境"

    # 构建用户记忆上下文
    mem = get_memory_manager(user_id)
    memory_text = mem.get_user_profile()
    recent_memories = await mem.search(enhanced_text, limit=5)
    recent_text = "\n".join([
        f"- {m['content']}" for m in recent_memories
    ]) if recent_memories else "无相关历史"
    memory_context = f"{memory_text}\n\n## 相关历史\n{recent_text}"

    # 构建双路 System Prompt
    system_a = DUAL_PATH_SYSTEM_TEMPLATE.format(
        path_instruction=DUAL_PATH_A_INSTRUCTION,
        memory_context=memory_context,
    )
    system_b = DUAL_PATH_SYSTEM_TEMPLATE.format(
        path_instruction=DUAL_PATH_B_INSTRUCTION,
        memory_context=memory_context,
    )

    # 创建独立客户端
    client_a = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    client_b = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    async def run_path(path: str, system_prompt: str, client: AsyncOpenAI):
        """运行单条推演路径，将结果放入队列"""
        try:
            stream = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_text},
                ],
                temperature=0.7,
                max_tokens=2560,
                stream=True,
            )
            full_text = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    await q.put({
                        "type": "content",
                        "path": path,
                        "text": delta.content,
                    })

            # 提取拓扑（若无则生成基础拓扑，保证两路都有沙盘）
            topology = parse_topology_v2(full_text)
            if not topology and len(full_text) > 100:
                keywords = re.findall(r'[一-鿿]{2,6}(?:风险|机会|问题|策略|路径|选择|危机|陷阱|优势|劣势)', full_text)
                nodes = [{"id": "n1", "label": "决策核心", "type": "core", "description": "当前分析的核心决策"}]
                for i, kw in enumerate(keywords[:7]):
                    nodes.append({"id": f"n{i+2}", "label": kw[:8], "type": "risk" if i%3==0 else ("safe" if i%3==1 else "psychology"), "description": kw})
                edges = []
                for i in range(1, min(len(nodes), 5)):
                    edges.append({"source": "n1", "target": f"n{i+1}", "label": "关联"})
                topology = {"topology_version": "2.0", "nodes": nodes, "edges": edges}

            # 先发拓扑，再发 done（done 触发队列关闭）
            await q.put({
                "type": "topology",
                "path": path,
                "data": topology,
            })
            await q.put({
                "type": "done",
                "path": path,
                "length": len(full_text),
                "elapsed_ms": 0,
            })

        except Exception as e:
            await q.put({
                "type": "error",
                "path": path,
                "text": str(e),
            })

    q = asyncio.Queue()

    async def event_stream():
        # 先发送元信息
        yield f"data: {json.dumps({'type': 'meta', 'path_a_label': '🌅 乐观路径 · 机会窗口', 'path_b_label': '🌑 悲观路径 · 风险防御'}, ensure_ascii=False)}\n\n"

        # 并行启动两条路径
        task_a = asyncio.create_task(run_path("a", system_a, client_a))
        task_b = asyncio.create_task(run_path("b", system_b, client_b))

        done_count = 0
        while done_count < 2:
            if await request.is_disconnected():
                task_a.cancel()
                task_b.cancel()
                break

            try:
                msg = await asyncio.wait_for(q.get(), timeout=0.1)
                if msg["type"] == "done":
                    done_count += 1
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                continue

        # 等待两个任务完全结束
        await asyncio.gather(task_a, task_b, return_exceptions=True)

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


# ═══════════════════════════════════════════
# OCR 辅助函数（V5.0 从 engine_v4 复用）
# ═══════════════════════════════════════════

def _ocr_single_image(data_uri: str) -> str:
    """对单张图片执行 OCR"""
    try:
        import tempfile
        import subprocess
        import base64 as b64

        if data_uri.startswith("data:"):
            header, b64_str = data_uri.split(",", 1)
        else:
            b64_str = data_uri

        img_bytes = b64.b64decode(b64_str)

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=tempfile.gettempdir())
        tmp.write(img_bytes)
        tmp.close()

        script = os.path.join(os.path.dirname(__file__), "ocr_helper.js")
        result = subprocess.run(
            ["node", script, tmp.name],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(__file__),
        )
        os.unlink(tmp.name)

        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            text = data.get("text", "").strip()
            if text and len(text) > 3:
                return text
        return ""
    except Exception:
        return ""


# ═══════════════════════════════════════════
# V6.0: 注册公共推演平台路由
# ═══════════════════════════════════════════
from public_api import router as public_router
app.include_router(public_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8920,
        reload=True,
        log_level="info",
    )
