"""
Retrieval Stream:从轨迹记忆库检索最相似的历史调查案例。

对应 ACRM 论文 Section 3.3 的 Retrieval Stream。
简化点:不用 Qwen-Embedding-8B,用 TF-IDF over 轨迹的文本描述做粗匹配。
反欺诈额外增加"图指纹"字段的 Jaccard 相似度(结构相似)。
"""

import re
from collections import Counter
from typing import Any

from .memory import TrajectoryMemory
from .state import State


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*", text.lower())


def _tf(tokens: list[str]) -> dict[str, float]:
    c = Counter(tokens)
    total = sum(c.values()) or 1
    return {k: v / total for k, v in c.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _graph_fingerprint_similarity(fp_a: dict, fp_b: dict) -> float:
    """结构指纹的 Jaccard(反欺诈独有)。"""
    if not fp_a or not fp_b:
        return 0.0
    keys = set(fp_a) | set(fp_b)
    if not keys:
        return 0.0

    def _canon(v):
        # 归一化:list/tuple 都转 sorted tuple,便于比较
        if isinstance(v, (list, tuple)):
            return tuple(sorted(str(x) for x in v))
        return v

    matches = sum(1 for k in keys if _canon(fp_a.get(k)) == _canon(fp_b.get(k)))
    return matches / len(keys)


def state_to_text(state: State) -> str:
    """把 State 序列化成文本,用于 TF-IDF。"""
    parts = [
        state.diagnostic_report,
        " ".join(state.action_history_summary),
        " ".join(f"{k}={v}" for k, v in state.key_metrics.items()),
    ]
    return " ".join(str(p) for p in parts)


class RetrievalStream:
    """
    检索 top-k 相似历史轨迹。
    返回:list[{"trajectory": dict, "similarity": float}]
    """

    def __init__(self, memory: TrajectoryMemory):
        self.memory = memory
        self._cache_tf: dict[int, dict[str, float]] = {}

    def _traj_text(self, traj: dict) -> str:
        """从存储的轨迹里提取用于匹配的文本。"""
        parts = [traj.get("trigger_reason", "")]
        for step in traj.get("steps", []):
            parts.append(step.get("state", {}).get("diagnostic_report", ""))
            parts.append(step.get("action", {}).get("type", ""))
        return " ".join(parts)

    def _traj_tf(self, i: int, traj: dict) -> dict[str, float]:
        if i not in self._cache_tf:
            self._cache_tf[i] = _tf(_tokenize(self._traj_text(traj)))
        return self._cache_tf[i]

    def search(self, state: State,
               current_fingerprint: dict | None = None,
               top_k: int = 3) -> list[dict[str, Any]]:
        q_tf = _tf(_tokenize(state_to_text(state)))
        scored = []
        for i, traj in enumerate(self.memory.retrievable()):
            text_sim = _cosine(q_tf, self._traj_tf(i, traj))
            fp_sim = _graph_fingerprint_similarity(
                current_fingerprint or {},
                traj.get("graph_fingerprint", {}),
            )
            # 反欺诈:结构相似度更重要,占 60%,文本相似度占 40%
            # (信用风险 ACRM 里文本足够,反欺诈的图 pattern 匹配是核心)
            sim = 0.4 * text_sim + 0.6 * fp_sim
            scored.append({"trajectory": traj, "similarity": sim,
                           "text_sim": text_sim, "fp_sim": fp_sim})
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    def confidence(self, results: list[dict]) -> float:
        """Top-1 相似度作为检索置信度。"""
        if not results:
            return 0.0
        return results[0]["similarity"]
