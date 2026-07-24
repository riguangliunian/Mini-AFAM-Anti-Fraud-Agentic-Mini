"""Typed state/action/outcome objects for production fraud diagnosis."""

from dataclasses import asdict, dataclass, field
from typing import Any


ACTION_SPECS = {
    "analyze_segment_drop": {"cost": 0.5, "kind": "diagnosis"},
    "run_sql_profile": {"cost": 0.6, "kind": "diagnosis"},
    "check_data_quality": {"cost": 0.7, "kind": "diagnosis"},
    "compute_feature_psi": {"cost": 0.7, "kind": "diagnosis"},
    "analyze_shap_shift": {"cost": 0.8, "kind": "diagnosis"},
    "analyze_behavior_sequence_shift": {"cost": 0.9, "kind": "diagnosis"},
    "analyze_graph_pattern_shift": {"cost": 0.9, "kind": "diagnosis"},
    "check_label_maturity": {"cost": 0.5, "kind": "diagnosis"},
    "run_replay_backtest": {"cost": 1.2, "kind": "evaluation"},
    "propose_feature_patch": {"cost": 0.8, "kind": "repair"},
    "adjust_threshold": {"cost": 0.6, "kind": "repair"},
    "update_rule": {"cost": 0.8, "kind": "repair"},
    "recommend_partial_retraining": {"cost": 1.0, "kind": "repair"},
    "recommend_full_retraining": {"cost": 1.4, "kind": "repair"},
    "escalate_to_human": {"cost": 0.0, "kind": "terminal"},
    "terminate": {"cost": 0.0, "kind": "terminal"},
}


ROOT_CAUSES = {
    "data_quality_issue",
    "feature_distribution_drift",
    "label_delay",
    "traffic_segment_shift",
    "attack_pattern_drift",
    "rule_interaction_issue",
    "threshold_miscalibration",
    "model_capacity_issue",
}


REPAIR_STRATEGIES = {
    "feature_patch",
    "threshold_adjustment",
    "rule_update",
    "partial_retraining",
    "full_retraining",
    "defer_until_label_mature",
    "human_review",
}


@dataclass
class DiagnosisState:
    alert_id: str
    model_name: str
    model_version: str
    round_num: int = 0
    monitor_alert: dict[str, Any] = field(default_factory=dict)
    metric_drop: dict[str, float] = field(default_factory=dict)
    affected_segments: dict[str, float] = field(default_factory=dict)
    data_quality: dict[str, Any] = field(default_factory=dict)
    psi: dict[str, Any] = field(default_factory=dict)
    shap: dict[str, Any] = field(default_factory=dict)
    behavior: dict[str, Any] = field(default_factory=dict)
    graph: dict[str, Any] = field(default_factory=dict)
    label_maturity: dict[str, Any] = field(default_factory=dict)
    sql_profile: dict[str, Any] = field(default_factory=dict)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    repair_candidate: dict[str, Any] = field(default_factory=dict)
    replay: dict[str, Any] = field(default_factory=dict)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    remaining_budget: float = 10.0
    retrieval_confidence: float = 0.0

    def to_prompt_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiagnosisAction:
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.action_type not in ACTION_SPECS:
            raise ValueError(f"Unknown diagnosis action: {self.action_type}")

    @property
    def cost(self) -> float:
        return float(ACTION_SPECS[self.action_type]["cost"])


@dataclass
class DiagnosisOutcome:
    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    cost: float = 0.0


@dataclass
class DiagnosisStep:
    state: DiagnosisState
    action: DiagnosisAction
    outcome: DiagnosisOutcome

    def to_dict(self) -> dict:
        return {
            "state": self.state.to_prompt_dict(),
            "action": asdict(self.action),
            "outcome": asdict(self.outcome),
        }


@dataclass
class DiagnosisTrajectory:
    alert_id: str
    trigger_reason: str
    category: str = ""
    difficulty: str = ""
    expected_root_cause: str = ""
    expected_repair: str = ""
    steps: list[DiagnosisStep] = field(default_factory=list)
    diagnosed_root_cause: str = "unknown"
    repair_strategy: str = ""
    success: bool = False
    total_cost: float = 0.0
    label: str = "pending_review"

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "trigger_reason": self.trigger_reason,
            "category": self.category,
            "difficulty": self.difficulty,
            "expected_root_cause": self.expected_root_cause,
            "expected_repair": self.expected_repair,
            "diagnosed_root_cause": self.diagnosed_root_cause,
            "repair_strategy": self.repair_strategy,
            "success": self.success,
            "total_cost": round(self.total_cost, 3),
            "rounds": len(self.steps),
            "label": self.label,
            "steps": [step.to_dict() for step in self.steps],
        }
