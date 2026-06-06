"""
认知破壁机 V3.0 — 核心推演引擎
支持多模态输入、Memory 注入、流式输出
"""
import json
import asyncio
import base64
import time
import subprocess
import tempfile
import os
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass
from openai import AsyncOpenAI
from memory_manager import MemoryManager


# ═══════════════════════════════════════════
# 认知破壁机 V2.0 — 硬核 System Prompt
# ═══════════════════════════════════════════

WALLBREAKER_SYSTEM_PROMPT = """# Role: 认知破壁机 V4.0 - 拓扑沙盘推演引擎 (Topology Wallbreaker)

# Profile:
你是一个深谙社会运行底层逻辑、资本收割套路与人性幽暗面的"现实主义破壁者"。
在 V4.0 中，你不仅要进行冷酷的文字解剖，还必须具备【多维沙盘推演能力】。
你需要将用户的单一决策，拆解为多个可能发生的"事件分支光点"，让用户看到决策的蝴蝶效应。

# 当前用户档案
{memory_context}

请引用用户历史数据中的"核心目标"和"性格弱点"作为衡量现实代价的锚点。

# Tone & Style:
1. 极度冷峻、带有黑色幽默与讽刺感，拒绝任何"心灵鸡汤"。
2. 视角降维：永远从"谁在利用你的弱点赚钱/获利"的【庄家视角】审视决策。
3. 字字见血，直接点破社会潜规则，用利益逻辑击碎幻想。

# Core Workflow (五刀推演 + 拓扑沙盘):
必须严格按以下两部分输出：

## Part 1: 文本解剖 (五刀推演)

### 🔪 第一刀：心理防御与认知盲区（内因）
- 用户正在使用的心理防御机制（情绪代偿、虚假投资回报率、同侪焦虑等）
- 至少 3 个"自我欺骗"信号
- 引用用户历史记忆中的冲动模式
> 💀 破壁人点评：[20字]

### 🔪 第二刀：利益链条与收割逻辑（外因）
- 谁是庄家？谁在割韭菜？
- 资本/商家/老板如何利用社会规训和算法诱导你？
- 用具体利益流向说明
> 💀 破壁人点评：[20字]

### 🔪 第三刀：阶层筹码与容错率计算（现实）
- 结合用户财务状况/阶层/目标的"底线压力测试"
- 富人试错叫投资，穷人试错叫破产——量化毁灭性打击
> 💀 破壁人点评：[20字]

### 🔪 第四刀：灰度博弈与反向操作（行动）
- 如果非做不可：如何止损？如何反向利用规则？最小代价试错？
- 2 条具体可执行的博弈策略
> 💀 破壁人点评：[20字]

### 🔪 第五刀：终极破壁拷问（灵魂暴击）
- 一个直击社会现实与个人命运交织的定制化问题
- 让用户感到不适，精准揭开一直回避的真相
> 💀 破壁人点评：[20字]

---

## Part 2: 拓扑沙盘数据 (V4.0 核心特征)

在文本推演结束后，你**必须且只能**输出一个合法的 JSON 代码块，用于前端渲染"决策衍生拓扑图"。

```json
{{
  "topology_version": "2.0",
  "nodes": [
    {{
      "id": "n1",
      "label": "核心决策",
      "type": "core",
      "description": "当前面临的核心决策困境"
    }},
    {{
      "id": "n2",
      "label": "风险分支",
      "type": "risk",
      "description": "可能导致的高危后果"
    }}
  ],
  "edges": [
    {{ "source": "n1", "target": "n2", "label": "导致" }}
  ]
}}
```

### JSON 节点类型 (type):
- "core": 核心决策节点
- "risk": 高危分支
- "safe": 破壁策略/安全路径
- "social": 社会规训/外部压力
- "psychology": 心理盲区/认知偏差
- "future": 未来衍生事件

### 铁律约束:
1. JSON 代码块必须被 ```json 和 ``` 包裹
2. JSON 必须是绝对合法的格式，禁止在 JSON 内部使用注释，禁止在 JSON 前后添加任何多余的废话
3. 必须包含至少 1 个 core 节点，总数不少于 8 个节点
4. 每个节点的 label 不超过 10 个字，description 不超过 50 字
5. edges 必须有因果关系标签

---

# 最终铁律:
1. 绝对禁止说"这取决于你的个人选择"或"只要你开心就好"
2. 始终用中文输出，文本部分控制在 1500-2500 字
3. 必须输出 Part 2 的 JSON 拓扑数据
"""


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

@dataclass
class SimulationInput:
    """推演输入"""
    user_id: str
    text: str = ""
    images_base64: Optional[List[str]] = None


@dataclass
class EngineConfig:
    """引擎配置"""
    model: str = "deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 2560
    api_key: str = ""
    base_url: str = "http://127.0.0.1:4000/v1"


# ═══════════════════════════════════════════
# 核心引擎
# ═══════════════════════════════════════════

class CognitiveEngine:
    """认知破壁机核心推演引擎"""

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.config = config or EngineConfig()
        self.memory = memory_manager or MemoryManager()

        # 初始化 OpenAI 兼容客户端
        self.client = AsyncOpenAI(
            api_key=self.config.api_key or "sk-placeholder",
            base_url=self.config.base_url,
        )

    def _ocr_image(self, data_uri: str) -> str:
        """
        对图片执行 OCR，提取文字

        Args:
            data_uri: Base64 data URI (如 data:image/png;base64,...)

        Returns:
            识别出的文字，失败返回 ""
        """
        try:
            # 解码 Base64
            if data_uri.startswith("data:"):
                header, b64 = data_uri.split(",", 1)
            else:
                b64 = data_uri

            img_bytes = base64.b64decode(b64)

            # 写入临时文件
            tmp = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, dir=tempfile.gettempdir()
            )
            tmp.write(img_bytes)
            tmp.close()

            # 调用 Node.js OCR 脚本
            script = os.path.join(os.path.dirname(__file__), "ocr_helper.js")
            result = subprocess.run(
                ["node", script, tmp.name],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(__file__),
            )

            # 清理临时文件
            os.unlink(tmp.name)

            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                text = data.get("text", "").strip()
                if text and len(text) > 3:
                    return text
                return ""
            return ""

        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    async def _build_messages(
        self,
        user_input: SimulationInput,
    ) -> List[Dict[str, Any]]:
        """
        构建多模态 messages 列表

        处理三种输入类型：
        1. 纯文本 → 标准 content 字符串
        2. 纯图片 → image_url content
        3. 文本+图片 → 混合 content 数组

        Args:
            user_input: 包含文本和/或图片的输入对象

        Returns:
            OpenAI 兼容的 messages 列表
        """
        # 1. 检索用户记忆
        memory_text = self.memory.get_user_profile()
        query = user_input.text if user_input.text else "用户上传了图片"
        recent_memories = await self.memory.search(query, limit=5)
        recent_text = "\n".join([
            f"- {m['content']}" for m in recent_memories
        ]) if recent_memories else "无相关历史"

        full_memory = f"{memory_text}\n\n## 相关历史\n{recent_text}"

        # 2. 构建 System Prompt
        system_prompt = WALLBREAKER_SYSTEM_PROMPT.format(
            memory_context=full_memory
        )

        # 3. 构建 User Message（多模态）
        has_images = bool(user_input.images_base64)
        has_text = bool(user_input.text.strip())

        # OCR 处理图片（DeepSeek 不支持 Vision，用 OCR 提取文字）
        ocr_texts = []
        if has_images:
            for img_b64 in user_input.images_base64:
                if not img_b64.startswith("data:"):
                    img_b64 = f"data:image/jpeg;base64,{img_b64}"
                ocr_result = self._ocr_image(img_b64)
                if ocr_result:
                    ocr_texts.append(ocr_result)

        # 构建增强后的文本：用户原文 + OCR 提取的图片文字
        enhanced_text = user_input.text.strip() if has_text else ""

        if ocr_texts:
            ocr_block = "\n\n---\n📷 **图片OCR识别内容**：\n"
            for i, t in enumerate(ocr_texts):
                ocr_block += f"\n[图片{i+1}]:\n{t}\n"
            ocr_block += "\n请结合以上图片中的文字信息，对用户的决策进行深度推演分析。\n---"
            enhanced_text += ocr_block

        # 如果没有文字也没有 OCR 结果
        if not enhanced_text.strip():
            if has_images and not ocr_texts:
                enhanced_text = "用户上传了图片，但未能识别出文字。请告知用户尝试更清晰的图片。"

        # 纯文本输入
        user_message = {
            "role": "user",
            "content": enhanced_text,
        }

        # 4. 组装完整 messages
        messages = [
            {"role": "system", "content": system_prompt},
            user_message,
        ]

        return messages

    async def simulate_stream(
        self,
        user_input: SimulationInput,
    ) -> AsyncGenerator[str, None]:
        """
        流式推演主函数

        将每一段输出以 SSE data 格式 yield 出去。

        Args:
            user_input: 包含用户文本和/或图片的输入

        Yields:
            SSE 格式的数据字符串: "data: {...}\n\n"
        """
        start_time = time.time()

        try:
            # 1. 发送思考提示
            yield self._sse_event("thinking", {
                "text": "🔍 正在检索你的历史决策记忆...",
                "memory_count": len(self.memory._local_memories),
            })

            # 2. 构建 messages（含记忆注入）
            messages = await self._build_messages(user_input)

            yield self._sse_event("thinking", {
                "text": "🧠 正在激活认知破壁引擎...",
            })

            # 3. 调用大模型流式接口
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )

            # 4. 发送内容开始信号
            yield self._sse_event("content_start", {
                "model": self.config.model,
                "timestamp": time.time(),
            })

            # 5. 流式传输内容
            full_text = ""
            char_count = 0
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    char_count += len(delta.content)
                    yield self._sse_event("content", {
                        "text": delta.content,
                    })
                    # 微小延迟，让前端有时间渲染，同时避免阻塞
                    if char_count % 200 == 0:
                        await asyncio.sleep(0.001)

            elapsed = time.time() - start_time

            # 6. 保存此次对话到记忆
            memory_text = f"用户事件: {user_input.text[:300]}"
            if full_text:
                # 提取关键盲区总结
                memory_text += f" | 分析长度: {len(full_text)}字"
            self.memory.add(
                content=memory_text,
                metadata={
                    "event_type": "wallbreaker_analysis",
                    "importance": 6,
                    "analysis_length": len(full_text),
                    "elapsed_ms": int(elapsed * 1000),
                    "has_images": bool(user_input.images_base64),
                },
            )

            # 7. 发送完成信号
            yield self._sse_event("done", {
                "length": len(full_text),
                "elapsed_ms": int(elapsed * 1000),
                "memory_updated": True,
            })

        except Exception as e:
            yield self._sse_event("error", {
                "text": f"引擎异常: {str(e)}",
                "code": type(e).__name__,
            })

    @staticmethod
    def _sse_event(event_type: str, data: Dict[str, Any]) -> str:
        """
        构建 SSE 事件字符串

        Args:
            event_type: 事件类型 (thinking/content/content_start/done/error)
            data: 事件数据

        Returns:
            "data: {...}\n\n" 格式的 SSE 字符串
        """
        payload = {"type": event_type, **data}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def encode_image_to_base64(file_path: str) -> str:
    """
    将图片文件编码为 Base64 字符串

    Args:
        file_path: 图片文件路径

    Returns:
        Base64 编码的图片字符串（不含 data URI 前缀）
    """
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_image_bytes_to_base64(data: bytes) -> str:
    """
    将图片字节数据编码为 Base64

    Args:
        data: 图片字节数据

    Returns:
        Base64 编码的图片字符串
    """
    return base64.b64encode(data).decode("utf-8")


def get_image_mime_type(data: bytes) -> str:
    """
    检测图片 MIME 类型

    Args:
        data: 图片字节数据的前几个字节

    Returns:
        MIME 类型字符串
    """
    if data[:4] == b"\x89PNG":
        return "image/png"
    elif data[:2] == b"\xff\xd8":
        return "image/jpeg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    elif data[:3] == b"GIF":
        return "image/gif"
    return "image/jpeg"  # 默认 JPEG
