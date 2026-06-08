"""
拓扑沙盘 JSON 解析器 — 共享模块
从 LLM 输出中提取并验证拓扑数据，engine_v5 / main / public_api 共用
"""
import json
import re
from typing import Optional, Dict, Any, List

VALID_NODE_TYPES = {"core", "risk", "safe", "social", "psychology", "future"}


def parse_topology(text: str, min_nodes: int = 3) -> Optional[Dict[str, Any]]:
    """
    从 LLM 输出文本中提取拓扑沙盘 JSON

    处理多种 LLM 输出格式：
    1. ```json ... ``` 或 ``` ... ``` 代码块
    2. 裸 JSON 对象

    自动修复常见 LLM 错误：尾部逗号、注释、多余逗号
    """
    if not text:
        return None

    # 模式1: 三反引号包裹的代码块（json 或裸）
    code_pattern = r'```(?:json)?\s*\n([\s\S]*?)\n```'
    matches = re.findall(code_pattern, text, re.DOTALL)
    if matches:
        candidates = [m for m in matches if '"topology_version"' in m or '"nodes"' in m]
        matches = candidates

    # 模式2: 直接找 JSON 对象
    if not matches:
        json_pattern = r'\{[\s\S]*"topology_version"[\s\S]*"nodes"[\s\S]*"edges"[\s\S]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

    for match in matches:
        cleaned = _clean_json(match.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            continue

        if not isinstance(data, dict):
            continue
        if "nodes" not in data or "edges" not in data:
            continue

        # 验证 + 清洗节点
        valid_nodes = _validate_nodes(data["nodes"])
        if len(valid_nodes) < min_nodes:
            continue

        # 验证 edges
        node_ids = {n["id"] for n in valid_nodes}
        valid_edges = _validate_edges(data["edges"], node_ids)

        return {
            "topology_version": data.get("topology_version", "3.0"),
            "adversarial_score": data.get("adversarial_score", 0.0),
            "nodes": valid_nodes,
            "edges": valid_edges,
        }

    return None


def _clean_json(raw: str) -> str:
    """清理 LLM 常见的 JSON 格式错误"""
    # 尾部逗号
    cleaned = re.sub(r',\s*}', '}', raw)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    # 单行注释
    cleaned = re.sub(r'//[^\n]*', '', cleaned)
    # 块注释
    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)
    return cleaned


def _validate_nodes(nodes: List[Dict]) -> List[Dict]:
    """验证并清洗节点列表"""
    valid = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if "id" not in node or "label" not in node:
            continue
        if node.get("type") not in VALID_NODE_TYPES:
            node["type"] = "core"
        valid.append(node)
    return valid


def _validate_edges(edges: List[Dict], node_ids: set) -> List[Dict]:
    """验证边引用有效性，补默认 confidence"""
    valid = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if "source" not in edge or "target" not in edge:
            continue
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            continue
        if "confidence" not in edge:
            edge["confidence"] = "medium"
        valid.append(edge)
    return valid
