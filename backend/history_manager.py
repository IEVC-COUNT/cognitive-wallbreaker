"""
认知破壁机 V4.0 — 历史推演记录管理器
每次推演保存为独立 JSON 文件，支持列表/详情/删除
"""
import json
import uuid
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


class HistoryManager:
    """推演历史记录管理器"""

    def __init__(self, user_id: str = "default", storage_dir: Optional[str] = None):
        self.user_id = user_id

        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(__file__), "..", "data", "history")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 用户历史目录
        self.user_dir = self.storage_dir / user_id
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        query: str,
        result: str,
        topology: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None,
        images_count: int = 0,
    ) -> str:
        """
        保存一次推演记录

        Args:
            query: 用户输入的决策问题
            result: 完整的推演文本
            topology: 拓扑沙盘 JSON 数据
            stats: 统计信息 (length, elapsed_ms)
            images_count: 图片数量

        Returns:
            记录 ID
        """
        record_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "id": record_id,
            "user_id": self.user_id,
            "query": query[:500],  # 截断超长输入
            "result": result,
            "topology": topology,
            "stats": stats or {},
            "images_count": images_count,
            "created_at": now,
        }

        file_path = self.user_dir / f"{record_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return record_id

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出用户的所有历史记录（摘要，不含完整结果文本）

        Args:
            limit: 最大返回数量

        Returns:
            记录摘要列表，按时间倒序
        """
        records = []

        # 遍历用户目录下的所有 JSON 文件
        json_files = sorted(
            self.user_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for file_path in json_files[:limit]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 摘要：不返回完整 result 文本，只返回前 200 字预览
                full_result = data.get("result", "")
                records.append({
                    "id": data.get("id", file_path.stem),
                    "query": data.get("query", ""),
                    "preview": full_result[:200] + ("..." if len(full_result) > 200 else ""),
                    "stats": data.get("stats", {}),
                    "has_topology": bool(data.get("topology")),
                    "images_count": data.get("images_count", 0),
                    "created_at": data.get("created_at", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return records

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单条完整记录

        Args:
            record_id: 记录 ID

        Returns:
            完整记录 dict，或 None
        """
        file_path = self.user_dir / f"{record_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return None

    def delete(self, record_id: str) -> bool:
        """
        删除一条记录

        Args:
            record_id: 记录 ID

        Returns:
            是否成功删除
        """
        file_path = self.user_dir / f"{record_id}.json"
        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    def stats(self) -> Dict[str, Any]:
        """返回历史记录统计"""
        json_files = list(self.user_dir.glob("*.json"))
        return {
            "user_id": self.user_id,
            "total_records": len(json_files),
            "storage_dir": str(self.user_dir),
        }
