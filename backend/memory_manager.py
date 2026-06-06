"""
认知破壁机 V4.0 — 长期记忆管理器
LLM 驱动的语义检索 + 结构化用户画像
零外部依赖：不依赖 Qdrant / sentence-transformers / mem0
"""
import json
import os
import re
import hashlib
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
from openai import AsyncOpenAI


# ═══════════════════════════════════════════
# 用户画像 JSON 模板
# ═══════════════════════════════════════════

PROFILE_TEMPLATE: Dict[str, Any] = {
    "occupation": "",
    "income_range": "",
    "core_goals": [],
    "cognitive_biases": [],
    "recent_themes": [],
    "personality_traits": "",
    "decision_patterns": "",
    "last_updated": None,
}


class MemoryManager:
    """
    用户记忆管理器

    V4.0 架构：
    - 本地 JSON 存储所有记忆（不变）
    - LLM 做语义检索：从最近记忆中选出与当前决策最相关的条目
    - LLM 定期提炼结构化用户画像，注入 System Prompt
    - 零外部向量数据库依赖
    """

    def __init__(
        self,
        user_id: str = "default",
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        storage_dir: Optional[str] = None,
    ):
        self.user_id = user_id
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "sk-placeholder")
        self.openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:4000/v1")
        self.model = os.getenv("WALLBREAKER_MODEL", "deepseek-v4-flash")

        # 持久化目录
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(__file__), "..", "data", "memory")
        self.storage_dir = Path(storage_dir)
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # 用户记忆文件
        self.memory_file = self.storage_dir / f"user_{self._safe_user_id(user_id)}.json"
        # 用户画像文件
        self.profile_file = self.storage_dir / f"profile_{self._safe_user_id(user_id)}.json"

        # LLM 客户端（用于记忆检索和画像提炼）
        self._llm = AsyncOpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
            timeout=15.0,
        )

        # 加载本地记忆
        self._local_memories: List[Dict[str, Any]] = self._load_local_memories()

        # 加载用户画像
        self._profile: Dict[str, Any] = self._load_profile()

        # 自上次提炼以来的新记忆数
        self._new_since_refine: int = 0

    # ═══════════════════════════════════════
    # 文件与工具
    # ═══════════════════════════════════════

    def _safe_user_id(self, uid: str) -> str:
        return hashlib.md5(uid.encode()).hexdigest()[:12]

    def _load_local_memories(self) -> List[Dict[str, Any]]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("memories", [])
            except (json.JSONDecodeError, KeyError):
                return []
        return []

    def _save_local_memories(self):
        data = {
            "user_id": self.user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "memories": self._local_memories,
        }
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_profile(self) -> Dict[str, Any]:
        if self.profile_file.exists():
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 合并模板，确保所有字段存在
                merged = {**PROFILE_TEMPLATE, **data}
                return merged
            except (json.JSONDecodeError, KeyError):
                pass
        return {**PROFILE_TEMPLATE}

    def _save_profile(self):
        self._profile["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self._profile, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════
    # 记忆 CRUD
    # ═══════════════════════════════════════

    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        添加一条记忆到本地存储

        Args:
            content: 记忆内容
            metadata: 附加元数据

        Returns:
            记忆 ID
        """
        meta = metadata or {}
        meta.update({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
        })

        memory_id = hashlib.md5(
            (content + str(time.time())).encode()
        ).hexdigest()[:16]

        entry = {
            "id": memory_id,
            "content": content,
            "metadata": meta,
            "created_at": meta["timestamp"],
        }

        self._local_memories.append(entry)

        # 限制本地记忆数量（最多 500 条）
        if len(self._local_memories) > 500:
            self._local_memories = self._local_memories[-500:]

        self._save_local_memories()

        # 标记画像需要更新
        self._new_since_refine += 1

        return memory_id

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        检索与当前决策最相关的历史记忆

        使用 LLM 做语义相关性判断，替代关键词匹配。
        - 记忆总数 ≤ limit：直接返回全部
        - 空 query：返回最近记忆
        - 其余：LLM 精选最相关条目

        Args:
            query: 检索查询
            limit: 返回数量上限

        Returns:
            相关记忆列表
        """
        total = len(self._local_memories)

        if total == 0:
            return []

        # 记忆很少，直接返回
        if total <= limit:
            return list(reversed(self._local_memories))

        # 空查询 → 返回最近记忆
        if not query or not query.strip():
            return list(reversed(self._local_memories[-limit:]))

        # ── LLM 语义检索 ──
        try:
            # 取最近 60 条记忆供 LLM 筛选
            pool = self._local_memories[-60:]

            # 构建轻量 prompt
            lines = []
            for m in pool:
                content_preview = m["content"][:200].replace("\n", " ")
                lines.append(f"[{m['id']}] {content_preview}")

            memory_list = "\n".join(lines)

            response = await self._llm.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": (
                        f"从以下记忆列表中选出与用户当前决策最相关的 {limit} 条记忆。\n"
                        f"只返回记忆ID组成的JSON数组，不要其他文字。\n\n"
                        f"用户决策：{query[:300]}\n\n"
                        f"记忆列表：\n{memory_list}\n\n"
                        f'返回格式：["id1","id2",...]'
                    ),
                }],
            )

            raw = response.choices[0].message.content or "[]"
            # 提取 JSON 数组
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                ids = json.loads(match.group())
                # 按 ID 找回原始记忆
                id_map = {m["id"]: m for m in pool}
                results = [id_map[i] for i in ids if i in id_map]
                if results:
                    return results[:limit]

        except Exception:
            pass  # LLM 检索失败 → 回退到时间排序

        # 回退：返回最近记忆
        return list(reversed(self._local_memories[-limit:]))

    def get_user_profile(self) -> str:
        """
        获取用户画像摘要文本，用于注入 System Prompt

        优先返回 LLM 提炼的结构化画像；
        画像为空时返回基于记忆统计的简易摘要。

        Returns:
            用户画像字符串
        """
        profile = self._profile

        # 检查画像是否有实质内容
        has_content = any([
            profile.get("occupation"),
            profile.get("income_range"),
            profile.get("core_goals"),
            profile.get("cognitive_biases"),
            profile.get("personality_traits"),
            profile.get("decision_patterns"),
        ])

        if has_content:
            parts = ["## 用户档案"]

            if profile.get("occupation"):
                parts.append(f"- 职业：{profile['occupation']}")
            if profile.get("income_range"):
                parts.append(f"- 收入区间：{profile['income_range']}")
            if profile.get("personality_traits"):
                parts.append(f"- 性格特征：{profile['personality_traits']}")
            if profile.get("decision_patterns"):
                parts.append(f"- 决策模式：{profile['decision_patterns']}")

            goals = profile.get("core_goals", [])
            if goals:
                parts.append(f"- 核心目标：{'、'.join(goals)}")

            biases = profile.get("cognitive_biases", [])
            if biases:
                parts.append(f"- 已识别认知偏差：{'、'.join(biases)}")

            themes = profile.get("recent_themes", [])
            if themes:
                parts.append(f"- 近期关注领域：{'、'.join(themes)}")

            if profile.get("last_updated"):
                parts.append(f"- 画像更新时间：{profile['last_updated'][:10]}")

            return "\n".join(parts)

        # 无结构化画像 → 从记忆统计简易摘要
        if not self._local_memories:
            return "暂无用户历史数据。"

        recent = sorted(
            self._local_memories,
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )[:10]

        parts = ["## 近期动态（画像未生成）"]
        for m in recent:
            ts = m.get("created_at", "")[:10]
            content = m.get("content", "")[:150].replace("\n", " ")
            parts.append(f"- [{ts}] {content}")

        return "\n".join(parts)

    async def refine_profile(self) -> bool:
        """
        使用 LLM 从新记忆中提炼/更新用户结构化画像

        触发条件：自上次提炼以来积累了 ≥ 5 条新记忆。
        会读取当前画像，结合新记忆，让 LLM 渐进更新。

        Returns:
            是否成功更新
        """
        if self._new_since_refine < 5:
            return False

        # 取自上次提炼以来的新记忆
        new_memories = self._local_memories[-self._new_since_refine:]

        # 构建新记忆摘要
        new_lines = []
        for m in new_memories:
            content = m["content"][:300].replace("\n", " ")
            ts = m.get("created_at", "")[:10]
            new_lines.append(f"[{ts}] {content}")

        new_text = "\n".join(new_lines)
        current_profile_json = json.dumps(self._profile, ensure_ascii=False, indent=2)

        try:
            response = await self._llm.chat.completions.create(
                model=self.model,
                temperature=0.3,
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": (
                        "你是一个用户画像分析助手。根据用户最新的决策对话记录，更新用户的结构化画像JSON。\n\n"
                        "## 当前画像\n"
                        f"{current_profile_json}\n\n"
                        "## 最新决策记录\n"
                        f"{new_text}\n\n"
                        "## 更新规则\n"
                        "1. 保留当前画像中仍然有效的字段\n"
                        "2. 从新记录中提取新的职业、目标、认知偏差等信息\n"
                        "3. 如果新记录与旧信息矛盾，以新记录为准\n"
                        "4. core_goals 每个目标不超过15字，最多5个\n"
                        "5. cognitive_biases 每条偏差不超过10字，最多5个\n"
                        "6. recent_themes 每个主题不超过8字，最多5个\n"
                        "7. 不确定的字段保持为空字符串或空数组，不要编造\n"
                        "8. 只返回JSON，不要其他文字\n\n"
                        "返回格式：\n"
                        "{\n"
                        '  "occupation": "职业",\n'
                        '  "income_range": "收入区间",\n'
                        '  "core_goals": ["目标1", "目标2"],\n'
                        '  "cognitive_biases": ["偏差1"],\n'
                        '  "recent_themes": ["主题1"],\n'
                        '  "personality_traits": "性格描述",\n'
                        '  "decision_patterns": "决策模式描述"\n'
                        "}"
                    ),
                }],
            )

            raw = response.choices[0].message.content or "{}"
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                new_profile = json.loads(match.group())
                # 合并而非覆盖：保留旧字段，新值覆盖
                self._profile.update({
                    k: v for k, v in new_profile.items()
                    if k in PROFILE_TEMPLATE
                })
                self._save_profile()
                self._new_since_refine = 0
                return True

        except Exception:
            pass  # 画像更新失败不影响主流程

        return False

    # ═══════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════

    def extract_and_save(self, conversation_text: str):
        """
        从对话中保存关键信息（简化版）

        完整版由 refine_profile() 定期触发 LLM 提炼。
        此方法做快速保存，积累数据供后续提炼。

        Args:
            conversation_text: 对话文本
        """
        # 保存对话摘要
        summary = conversation_text[:1000]
        self.add(
            content=f"[对话记录] {summary}",
            metadata={
                "event_type": "conversation",
                "importance": 3,
                "length": len(conversation_text),
            },
        )

        # 保存关键决策
        if len(conversation_text) > 50:
            key_points = conversation_text[:200].replace("\n", " ")
            self.add(
                content=f"[决策分析] {key_points}",
                metadata={
                    "event_type": "decision_analysis",
                    "importance": 7,
                },
            )

    def clear_user_memories(self):
        """清除当前用户的所有记忆和画像"""
        self._local_memories = []
        self._save_local_memories()
        self._profile = {**PROFILE_TEMPLATE}
        self._save_profile()
        self._new_since_refine = 0

    def stats(self) -> Dict[str, Any]:
        """返回记忆统计信息"""
        has_profile = any([
            self._profile.get("occupation"),
            self._profile.get("core_goals"),
            self._profile.get("cognitive_biases"),
        ])
        return {
            "user_id": self.user_id,
            "total_memories": len(self._local_memories),
            "search_engine": "LLM 语义检索",
            "profile_ready": has_profile,
            "new_since_refine": self._new_since_refine,
            "storage_file": str(self.memory_file),
            "profile_file": str(self.profile_file),
            "last_updated": (
                max(m.get("created_at", "") for m in self._local_memories)
                if self._local_memories
                else None
            ),
        }
