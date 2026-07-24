"""
State / Action / Outcome 类型定义。

对应 ACRM 论文里的 typed workflow trajectory τ = {(s_t, a_t, o_t)}。
反欺诈版本的关键扩展:
- State 里显式带 label_maturity 和图诊断摘要
- Action 从 10 个预定义模板中选,避免 LLM 生成非法参数
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import time


@dataclass
class State:
    """
    调查过程中的累积状态。

    diagnostic_report:GraphMiner 每轮产出的自然语言诊断报告(LLM 主要读这个)
    suspect_set:当前可疑用户集合
    key_metrics:数值指标快照
    label_maturity:平均标签成熟度 [0,1](反欺诈独有的字段)
    action_history_summary:已执行动作的简短摘要
    retrieval_confidence:上一次 retrieval 的置信度(<0.6 表示新型攻击)
    """
    alert_id: str
    round_num: int = 0
    diagnostic_report: str = ""
    suspect_set: list[str] = field(default_factory=list)
    key_metrics: dict[str, Any] = field(default_factory=dict)
    label_maturity: float = 0.5
    action_history_summary: list[str] = field(default_factory=list)
    retrieval_confidence: float = 1.0
    graph_fingerprint: dict[str, Any] = field(default_factory=dict)
    pattern_assessment: dict[str, Any] = field(default_factory=dict)

    def to_prompt_dict(self) -> dict:
        """裁剪后喂给 LLM 的字典(不含冗余字段)。"""
        return {
            "alert_id": self.alert_id,
            "round": self.round_num,
            "diagnostic_report": self.diagnostic_report,
            "suspect_count": len(self.suspect_set),
            "key_metrics": self.key_metrics,
            "label_maturity": round(self.label_maturity, 2),
            "past_actions": self.action_history_summary,
            "retrieval_confidence": round(self.retrieval_confidence, 2),
            "graph_fingerprint": self.graph_fingerprint,
            "pattern_assessment": self.pattern_assessment,
        }


# 预定义动作模板(核心思想:动作是"语义级"的)
ACTION_TEMPLATES = {
    "expand_neighbors": {
        "description": "从种子集合扩展 K 度邻居,按边类型过滤",
        "params": ["seeds", "hop", "edge_type"],
    },
    "find_community": {
        "description": "在子图上跑社区发现",
        "params": ["algo", "min_size"],
    },
    "check_shared_entity": {
        "description": "统计共享同一实体的用户数",
        "params": ["entity_type"],
    },
    "check_temporal_burst": {
        "description": "检测短时间内集中申请的模式",
        "params": ["window_hours"],
    },
    "compute_risk_score": {
        "description": "对可疑集合计算综合风险分",
        "params": ["features"],
    },
    "generate_rule": {
        "description": "生成一条拦截规则(须组合结构+属性)",
        "params": ["pattern", "coverage_min", "confidence_threshold"],
    },
    "shadow_replay": {
        "description": "在历史流量上回放新规则,评估召回和误伤",
        "params": ["rule_id", "replay_days"],
    },
    "adversarial_probe": {
        "description": "红队自测,尝试常见绕过手段",
        "params": ["rule_id", "bypass_strategies"],
    },
    "escalate_to_human": {
        "description": "将案子升级到人工调查",
        "params": ["reason"],
    },
    "terminate": {
        "description": "输出最终结论并结束",
        "params": ["verdict", "confidence", "recommendations"],
    },
}


@dataclass
class Action:
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def __post_init__(self):
        if self.action_type not in ACTION_TEMPLATES:
            raise ValueError(f"Unknown action_type: {self.action_type}")

    def short(self) -> str:
        return f"{self.action_type}({', '.join(f'{k}={v}' for k,v in self.params.items())})"


@dataclass
class Outcome:
    """动作执行后的结果。"""
    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    new_suspects: list[str] = field(default_factory=list)


@dataclass
class TrajectoryStep:
    state: State
    action: Action
    outcome: Outcome

    def to_dict(self) -> dict:
        # 过滤 outcome.metrics 中以 _ 开头的内部字段(如 _rule_obj)
        clean_metrics = {k: v for k, v in self.outcome.metrics.items()
                          if not k.startswith("_")}
        return {
            "state": self.state.to_prompt_dict(),
            "action": {"type": self.action.action_type,
                       "params": self.action.params,
                       "rationale": self.action.rationale},
            "outcome": {"success": self.outcome.success,
                        "metrics": clean_metrics,
                        "note": self.outcome.note,
                        "new_suspects_count": len(self.outcome.new_suspects)},
        }


@dataclass
class Trajectory:
    """一次完整的调查轨迹(用于 Memory 和最终报告)。"""
    alert_id: str
    trigger_reason: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    verdict: Optional[str] = None  # "fraud_confirmed" | "not_fraud" | "escalate"
    final_confidence: float = 0.0
    total_seconds: float = 0.0
    label: Optional[str] = None  # "accepted" | "rejected"(事后打的,用于 DPO 训练)

    def to_dict(self) -> dict:
        final_fp = self.steps[-1].state.graph_fingerprint if self.steps else {}
        return {
            "alert_id": self.alert_id,
            "trigger_reason": self.trigger_reason,
            "steps": [s.to_dict() for s in self.steps],
            "verdict": self.verdict,
            "final_confidence": self.final_confidence,
            "rounds": len(self.steps),
            "total_seconds": self.total_seconds,
            "label": self.label,
            "graph_fingerprint": final_fp,
        }
