"""
认知破壁机 V5.0 — 多智能体对抗推演引擎
7 Agent 编排：五刀(并行+串行) → 魔鬼代言人 → 终审法官

架构:
  阶段1 (并行):  Agent 1+2+3 同时跑
  阶段2 (串行):  Agent 4 → Agent 5
  阶段3 (串行):  Agent 6 魔鬼代言人
  阶段4 (串行):  Agent 7 终审判决 + 拓扑沙盘
"""
import json
import asyncio
import time
import re
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass, field
from openai import AsyncOpenAI

from memory_manager import MemoryManager
from prompts_v5 import AGENT_CONFIG, get_agent_prompt


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

@dataclass
class V5SimulationInput:
    """V5 推演输入"""
    user_id: str
    text: str = ""
    images_base64: Optional[list] = None


@dataclass
class V5EngineConfig:
    """V5 引擎配置"""
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    # 各 Agent 超时（秒）
    agent_timeout: float = 30.0


@dataclass
class AgentResult:
    """单个 Agent 的执行结果"""
    agent_key: str
    name: str
    emoji: str
    full_text: str = ""
    success: bool = False
    elapsed_ms: float = 0
    error: str = ""


# ═══════════════════════════════════════════
# 核心编排引擎
# ═══════════════════════════════════════════

class V5CognitiveEngine:
    """V5.0 多智能体对抗推演引擎"""

    def __init__(
        self,
        config: Optional[V5EngineConfig] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.config = config or V5EngineConfig()
        self.memory = memory_manager or MemoryManager()

        self.client = AsyncOpenAI(
            api_key=self.config.api_key or "sk-placeholder",
            base_url=self.config.base_url,
        )

    # ── 工具方法 ────────────────────────────

    @staticmethod
    def _sse_event(event_type: str, data: Dict[str, Any]) -> str:
        """构建 SSE 事件字符串"""
        payload = {"type": event_type, **data}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def _run_single_agent(
        self,
        agent_key: str,
        system_prompt: str,
        user_message: str,
    ) -> AgentResult:
        """
        运行单个 Agent，流式输出 content chunk

        Args:
            agent_key: Agent 标识
            system_prompt: 格式化后的 System Prompt
            user_message: 用户输入文本

        Returns:
            AgentResult 包含完整输出
        """
        config = AGENT_CONFIG[agent_key]
        result = AgentResult(
            agent_key=agent_key,
            name=config["name"],
            emoji=config["emoji"],
        )

        start_time = time.time()

        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"],
                    stream=True,
                ),
                timeout=self.config.agent_timeout,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    result.full_text += delta.content

            result.success = True

        except asyncio.TimeoutError:
            result.error = f"{config['name']} 超时（{self.config.agent_timeout}s）"
            if result.full_text:
                result.success = True  # 部分输出也接受
        except Exception as e:
            result.error = f"{config['name']} 异常: {str(e)[:200]}"
            if result.full_text:
                result.success = True

        result.elapsed_ms = (time.time() - start_time) * 1000
        return result

    # ── 记忆检索 ────────────────────────────

    async def _build_memory_context(self, user_text: str) -> str:
        """构建用户记忆上下文"""
        memory_text = self.memory.get_user_profile()
        recent_memories = await self.memory.search(user_text, limit=5)
        recent_text = "\n".join([
            f"- {m['content']}" for m in recent_memories
        ]) if recent_memories else "无相关历史"

        return f"{memory_text}\n\n## 相关历史\n{recent_text}"

    # ── 主推演流程 ──────────────────────────

    async def simulate_stream(
        self,
        user_input: V5SimulationInput,
    ) -> AsyncGenerator[str, None]:
        """
        V5.0 多智能体对抗推演 — SSE 流式输出

        阶段:
          1. [并行] Agent 1-3: 心理刀 + 利益刀 + 阶层刀
          2. [串行] Agent 4 → 5: 博弈刀 → 灵魂刀
          3. [串行] Agent 6: 魔鬼代言人
          4. [串行] Agent 7: 终审法官 + 拓扑沙盘
        """
        total_start = time.time()
        user_text = user_input.text.strip()

        try:
            # ═══════════════════════════════════
            # 前置：记忆检索
            # ═══════════════════════════════════
            yield self._sse_event("phase", {
                "phase": "memory",
                "text": "🔍 检索用户历史决策记忆...",
            })

            memory_context = await self._build_memory_context(user_text)

            yield self._sse_event("phase", {
                "phase": "memory_done",
                "text": "✅ 记忆检索完成",
                "memory_count": len(self.memory._local_memories),
            })

            # ═══════════════════════════════════
            # 阶段 1: 并行运行 Agent 1-3
            # ═══════════════════════════════════
            yield self._sse_event("phase", {
                "phase": "blades_1_3",
                "text": "⚔️ 三刀齐出：心理·利益·阶层 同时推演...",
            })

            # 启动并行任务
            task_psychology = asyncio.create_task(
                self._run_single_agent(
                    "psychology",
                    get_agent_prompt("psychology", memory_context=memory_context),
                    f"请分析以下决策：\n{user_text}",
                )
            )
            task_interest = asyncio.create_task(
                self._run_single_agent(
                    "interest",
                    get_agent_prompt("interest", memory_context=memory_context),
                    f"请分析以下决策：\n{user_text}",
                )
            )
            task_class = asyncio.create_task(
                self._run_single_agent(
                    "class",
                    get_agent_prompt("class", memory_context=memory_context),
                    f"请分析以下决策：\n{user_text}",
                )
            )

            # 逐个收割结果（哪个先完成先播报）
            pending = {
                task_psychology: "psychology",
                task_interest: "interest",
                task_class: "class",
            }

            results_1_3: Dict[str, AgentResult] = {}

            async for coro in asyncio.as_completed(pending.keys()):
                agent_key = pending[coro]
                result = await coro
                results_1_3[agent_key] = result

                cfg = AGENT_CONFIG[agent_key]
                if result.success:
                    yield self._sse_event("agent_done", {
                        "agent": agent_key,
                        "name": cfg["name"],
                        "emoji": cfg["emoji"],
                        "text": result.full_text,
                        "elapsed_ms": int(result.elapsed_ms),
                    })
                else:
                    yield self._sse_event("agent_error", {
                        "agent": agent_key,
                        "name": cfg["name"],
                        "error": result.error,
                    })

            # ═══════════════════════════════════
            # 阶段 2: 串行 Agent 4 → 5
            # ═══════════════════════════════════
            yield self._sse_event("phase", {
                "phase": "blades_4_5",
                "text": "♟️ 博弈策略师入场，读取前三刀战报...",
            })

            # 构建前序摘要给 Agent 4
            summary_1_3 = self._build_blade_summary(results_1_3)
            game_prompt = get_agent_prompt(
                "game",
                memory_context=memory_context,
                previous_blades_summary=summary_1_3,
            )

            result_game = await self._run_single_agent(
                "game",
                game_prompt,
                f"基于前三刀的分析摘要，为以下决策制定博弈策略：\n{user_text}",
            )

            if result_game.success:
                yield self._sse_event("agent_done", {
                    "agent": "game",
                    "name": AGENT_CONFIG["game"]["name"],
                    "emoji": AGENT_CONFIG["game"]["emoji"],
                    "text": result_game.full_text,
                    "elapsed_ms": int(result_game.elapsed_ms),
                })
            else:
                yield self._sse_event("agent_error", {
                    "agent": "game",
                    "name": AGENT_CONFIG["game"]["name"],
                    "error": result_game.error,
                })

            # Agent 5: 灵魂刀
            summary_1_4 = summary_1_3 + "\n\n" + (
                result_game.full_text[:500] if result_game.success else ""
            )
            soul_prompt = get_agent_prompt(
                "soul",
                memory_context=memory_context,
                previous_blades_summary=summary_1_4,
            )

            yield self._sse_event("phase", {
                "phase": "blade_5",
                "text": "💀 灵魂暴击拷问者就位，磨刀中...",
            })

            result_soul = await self._run_single_agent(
                "soul",
                soul_prompt,
                f"基于前四刀的分析摘要，对以下决策提出灵魂拷问：\n{user_text}",
            )

            if result_soul.success:
                yield self._sse_event("agent_done", {
                    "agent": "soul",
                    "name": AGENT_CONFIG["soul"]["name"],
                    "emoji": AGENT_CONFIG["soul"]["emoji"],
                    "text": result_soul.full_text,
                    "elapsed_ms": int(result_soul.elapsed_ms),
                })
            else:
                yield self._sse_event("agent_error", {
                    "agent": "soul",
                    "name": AGENT_CONFIG["soul"]["name"],
                    "error": result_soul.error,
                })

            # ═══════════════════════════════════
            # 阶段 3: 魔鬼代言人
            # ═══════════════════════════════════
            yield self._sse_event("phase", {
                "phase": "devil",
                "text": "😈 魔鬼代言人入场，逐刀拆台...",
            })

            all_blades = self._merge_all_blades(
                results_1_3, result_game, result_soul
            )
            devil_prompt = get_agent_prompt(
                "devil",
                memory_context=memory_context,
                all_blades_output=all_blades,
            )

            result_devil = await self._run_single_agent(
                "devil",
                devil_prompt,
                f"五刀分析师已完成对以下决策的分析。请逐刀反驳：\n{user_text}",
            )

            if result_devil.success:
                yield self._sse_event("agent_done", {
                    "agent": "devil",
                    "name": AGENT_CONFIG["devil"]["name"],
                    "emoji": AGENT_CONFIG["devil"]["emoji"],
                    "text": result_devil.full_text,
                    "elapsed_ms": int(result_devil.elapsed_ms),
                })
            else:
                yield self._sse_event("agent_error", {
                    "agent": "devil",
                    "name": AGENT_CONFIG["devil"]["name"],
                    "error": result_devil.error,
                })

            # ═══════════════════════════════════
            # 阶段 4: 终审法官 + 拓扑沙盘
            # ═══════════════════════════════════
            yield self._sse_event("phase", {
                "phase": "judge",
                "text": "⚖️ 首席推演官终审判决，生成拓扑沙盘...",
            })

            judge_prompt = get_agent_prompt(
                "judge",
                memory_context=memory_context,
                all_blades_output=all_blades,
                devils_advocate_output=result_devil.full_text if result_devil.success else "魔鬼代言人未输出",
            )

            result_judge = await self._run_single_agent(
                "judge",
                judge_prompt,
                f"综合所有推演和反驳，对以下决策做出终审判决：\n{user_text}",
            )

            if result_judge.success:
                # 提取拓扑数据
                topology = self._parse_topology(result_judge.full_text)

                yield self._sse_event("agent_done", {
                    "agent": "judge",
                    "name": AGENT_CONFIG["judge"]["name"],
                    "emoji": AGENT_CONFIG["judge"]["emoji"],
                    "text": result_judge.full_text,
                    "elapsed_ms": int(result_judge.elapsed_ms),
                })

                if topology:
                    yield self._sse_event("topology", {"data": topology})
            else:
                yield self._sse_event("agent_error", {
                    "agent": "judge",
                    "name": AGENT_CONFIG["judge"]["name"],
                    "error": result_judge.error,
                })

            # ═══════════════════════════════════
            # 收尾：保存记忆 + 完成信号
            # ═══════════════════════════════════
            total_elapsed = int((time.time() - total_start) * 1000)

            # 保存此次推演到记忆
            self.memory.add(
                content=f"用户事件: {user_text[:300]}",
                metadata={
                    "event_type": "wallbreaker_v5_analysis",
                    "importance": 7,
                    "agents_count": 7,
                    "agents_succeeded": sum([
                        1 for r in list(results_1_3.values()) + [result_game, result_soul, result_devil, result_judge]
                        if r.success
                    ]),
                    "elapsed_ms": total_elapsed,
                },
            )

            yield self._sse_event("done", {
                "version": "5.0",
                "elapsed_ms": total_elapsed,
                "agents": {
                    "psychology": results_1_3.get("psychology", AgentResult("psychology", "", "")).success,
                    "interest": results_1_3.get("interest", AgentResult("interest", "", "")).success,
                    "class": results_1_3.get("class", AgentResult("class", "", "")).success,
                    "game": result_game.success,
                    "soul": result_soul.success,
                    "devil": result_devil.success,
                    "judge": result_judge.success,
                },
                "memory_updated": True,
            })

        except Exception as e:
            yield self._sse_event("error", {
                "text": f"V5 引擎异常: {str(e)}",
                "code": type(e).__name__,
            })

    # ── 辅助方法 ────────────────────────────

    def _build_blade_summary(self, results: Dict[str, AgentResult]) -> str:
        """从 Agent 1-3 结果构建摘要，用于喂给 Agent 4"""
        parts = []
        order = ["psychology", "interest", "class"]
        for key in order:
            if key in results and results[key].success:
                text = results[key].full_text
                # 取前 400 字作为摘要
                summary = text[:400] + ("..." if len(text) > 400 else "")
                parts.append(f"### {AGENT_CONFIG[key]['name']}\n{summary}")
            else:
                parts.append(f"### {AGENT_CONFIG[key]['name']}\n（分析失败）")
        return "\n\n".join(parts)

    def _merge_all_blades(
        self,
        results_1_3: Dict[str, AgentResult],
        result_game: AgentResult,
        result_soul: AgentResult,
    ) -> str:
        """合并全部五刀输出为完整文本，喂给魔鬼代言人和法官"""
        parts = []
        order = [
            ("psychology", "第一刀·心理防御"),
            ("interest", "第二刀·利益链条"),
            ("class", "第三刀·阶层容错"),
        ]

        for key, title in order:
            if key in results_1_3 and results_1_3[key].success:
                parts.append(f"## {title}\n{results_1_3[key].full_text}")
            else:
                parts.append(f"## {title}\n（分析失败）")

        if result_game.success:
            parts.append(f"## 第四刀·灰度博弈\n{result_game.full_text}")
        if result_soul.success:
            parts.append(f"## 第五刀·灵魂拷问\n{result_soul.full_text}")

        return "\n\n---\n\n".join(parts)

    def _parse_topology(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从终审法官的输出中提取拓扑沙盘 JSON

        复用 V4.0 的解析逻辑（多模式正则匹配 + 验证 + 修复）
        """
        if not text:
            return None

        # 模式1: ```json ... ```
        json_pattern = r'```json\s*\n(.*?)\n\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)

        # 模式2: ``` ... ```
        if not matches:
            json_pattern = r'```\s*\n(\{[\s\S]*?\})\s*\n\s*```'
            matches = re.findall(json_pattern, text, re.DOTALL)

        # 模式3: 直接找 JSON 对象
        if not matches:
            json_pattern = r'\{[\s\S]*"topology_version"[\s\S]*"nodes"[\s\S]*"edges"[\s\S]*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)

        for match in matches:
            cleaned = match.strip()

            # 修复常见 AI 输出错误
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

            # 验证并修复节点
            valid_types = {"core", "risk", "safe", "social", "psychology", "future"}
            valid_nodes = []
            for node in data["nodes"]:
                if not isinstance(node, dict):
                    continue
                if "id" not in node or "label" not in node:
                    continue
                if node.get("type") not in valid_types:
                    node["type"] = "core"
                valid_nodes.append(node)

            # 验证 edges 引用
            node_ids = {n["id"] for n in valid_nodes}
            valid_edges = []
            for edge in data["edges"]:
                if not isinstance(edge, dict):
                    continue
                if "source" not in edge or "target" not in edge:
                    continue
                if edge["source"] in node_ids and edge["target"] in node_ids:
                    # 确保有 confidence 字段
                    if "confidence" not in edge:
                        edge["confidence"] = "medium"
                    valid_edges.append(edge)

            if len(valid_nodes) < 3:
                continue

            return {
                "topology_version": data.get("topology_version", "3.0"),
                "adversarial_score": data.get("adversarial_score", 0.8),
                "nodes": valid_nodes,
                "edges": valid_edges,
            }

        return None


# ═══════════════════════════════════════════
# 快速模式：3 Agent 降级版
# ═══════════════════════════════════════════

class V5FastEngine(V5CognitiveEngine):
    """
    V5.0 快速模式 — 只用 3 个 Agent
    心理刀 + 利益刀 + 终审法官（法官兼任博弈/灵魂/魔鬼职责）
    3 次 LLM 调用，约 V4.0 成本的 1.5 倍
    """

    async def simulate_stream(
        self,
        user_input: V5SimulationInput,
    ) -> AsyncGenerator[str, None]:
        total_start = time.time()
        user_text = user_input.text.strip()

        try:
            # 记忆检索
            yield self._sse_event("phase", {
                "phase": "memory",
                "text": "🔍 快速模式：检索记忆...",
            })
            memory_context = await self._build_memory_context(user_text)

            # 并行：心理 + 利益
            yield self._sse_event("phase", {
                "phase": "blades_fast",
                "text": "⚡ 快速双刀并行推演...",
            })

            task_psych = asyncio.create_task(
                self._run_single_agent(
                    "psychology",
                    get_agent_prompt("psychology", memory_context=memory_context),
                    f"请分析以下决策：\n{user_text}",
                )
            )
            task_int = asyncio.create_task(
                self._run_single_agent(
                    "interest",
                    get_agent_prompt("interest", memory_context=memory_context),
                    f"请分析以下决策：\n{user_text}",
                )
            )

            results = {}
            async for coro in asyncio.as_completed([task_psych, task_int]):
                result = await coro
                # 找出是哪个 agent
                for key in ["psychology", "interest"]:
                    if result.agent_key == key:
                        results[key] = result
                        break

                if result.success:
                    yield self._sse_event("agent_done", {
                        "agent": result.agent_key,
                        "name": AGENT_CONFIG[result.agent_key]["name"],
                        "emoji": AGENT_CONFIG[result.agent_key]["emoji"],
                        "text": result.full_text,
                        "elapsed_ms": int(result.elapsed_ms),
                    })

            # 快速法官（承担剩余所有职责）
            yield self._sse_event("phase", {
                "phase": "judge_fast",
                "text": "⚖️ 快速判决：法官兼任博弈+灵魂+魔鬼...",
            })

            blades_text = self._merge_all_blades(
                results,
                AgentResult("game", "", ""),
                AgentResult("soul", "", ""),
            )

            # 快速法官 Prompt: 合并了博弈、灵魂、魔鬼的职责
            fast_judge_prompt = get_agent_prompt(
                "judge",
                memory_context=memory_context,
                all_blades_output=blades_text,
                devils_advocate_output="（快速模式：法官自行提出反驳）请你在判决中同时完成以下职责：\n1. 提出博弈策略\n2. 提出灵魂拷问\n3. 自我反驳并检验论证强度\n4. 做出终审判决并输出拓扑JSON",
            )

            result_judge = await self._run_single_agent(
                "judge",
                fast_judge_prompt,
                f"请对以下决策进行全面推演分析（含博弈策略、灵魂拷问、自我反驳）：\n{user_text}",
            )

            if result_judge.success:
                topology = self._parse_topology(result_judge.full_text)

                yield self._sse_event("agent_done", {
                    "agent": "judge",
                    "name": "首席推演官（快速模式）",
                    "emoji": "⚡",
                    "text": result_judge.full_text,
                    "elapsed_ms": int(result_judge.elapsed_ms),
                })

                if topology:
                    yield self._sse_event("topology", {"data": topology})

            total_elapsed = int((time.time() - total_start) * 1000)

            self.memory.add(
                content=f"[快速模式] 用户事件: {user_text[:300]}",
                metadata={
                    "event_type": "wallbreaker_v5_fast",
                    "importance": 6,
                    "elapsed_ms": total_elapsed,
                },
            )

            yield self._sse_event("done", {
                "version": "5.0-fast",
                "elapsed_ms": total_elapsed,
                "mode": "fast",
                "memory_updated": True,
            })

        except Exception as e:
            yield self._sse_event("error", {
                "text": f"V5 快速引擎异常: {str(e)}",
                "code": type(e).__name__,
            })
