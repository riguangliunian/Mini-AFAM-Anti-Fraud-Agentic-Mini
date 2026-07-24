"""模型刷新工作流的 typed State / Action / Outcome / Trajectory。"""

from dataclasses import asdict, dataclass, field
from typing import Any


ACTION_SPECS = {
    "analyze_segment_performance": {"cost": 0.5, "kind": "diagnosis"},
    "analyze_feature_drift": {"cost": 0.5, "kind": "diagnosis"},
    "analyze_graph_drift": {"cost": 0.8, "kind": "diagnosis"},
    "analyze_label_maturity": {"cost": 0.4, "kind": "diagnosis"},
    "inspect_false_negative_clusters": {"cost": 0.8, "kind": "diagnosis"},
    "inspect_false_positive_clusters": {"cost": 0.8, "kind": "diagnosis"},
    "adjust_training_window": {"cost": 1.0, "kind": "intervention"},
    "reweight_mature_samples": {"cost": 1.0, "kind": "intervention"},
    "mine_hard_negatives": {"cost": 1.2, "kind": "intervention"},
    "add_graph_relation_features": {"cost": 1.5, "kind": "intervention"},
    "repair_data_pipeline": {"cost": 1.0, "kind": "intervention"},
    "fine_tune_gnn": {"cost": 3.0, "kind": "training"},
    "run_out_of_time_test": {"cost": 0.8, "kind": "validation"},
    "run_shadow_evaluation": {"cost": 0.8, "kind": "validation"},
    "recommend_rollback": {"cost": 0.0, "kind": "terminal"},
    "escalate_to_human": {"cost": 0.0, "kind": "terminal"},
    "terminate": {"cost": 0.0, "kind": "terminal"},
}


@dataclass
class RefreshState:
    event_id: str
    model_version: str
    round_num: int = 0
    baseline_metrics: dict[str, float] = field(default_factory=dict)
    current_metrics: dict[str, float] = field(default_factory=dict)
    drift_signals: dict[str, float] = field(default_factory=dict)
    segment_degradation: dict[str, float] = field(default_factory=dict)
    label_context: dict[str, float] = field(default_factory=dict)
    diagnosis: dict[str, Any] = field(default_factory=dict)
    interventions: list[str] = field(default_factory=list)
    candidate_metrics: dict[str, float] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    remaining_budget: float = 10.0
    remaining_experiments: int = 3
    retrieval_confidence: float = 0.0

    def to_prompt_dict(self) -> dict:
        return asdict(self)


@dataclass
class RefreshAction:
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def __post_init__(self):
        if self.action_type not in ACTION_SPECS:
            raise ValueError(f"Unknown refresh action: {self.action_type}")

    @property
    def cost(self) -> float:
        return float(ACTION_SPECS[self.action_type]["cost"])


@dataclass
class RefreshOutcome:
    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    cost: float = 0.0


@dataclass
class RefreshStep:
    state: RefreshState
    action: RefreshAction
    outcome: RefreshOutcome

    def to_dict(self) -> dict:
        return {
            "state": self.state.to_prompt_dict(),
            "action": asdict(self.action),
            "outcome": asdict(self.outcome),
        }


@dataclass
class RefreshTrajectory:
    event_id: str
    trigger_reason: str
    steps: list[RefreshStep] = field(default_factory=list)
    diagnosed_cause: str = "unknown"
    expected_cause: str = ""
    recommendation: str = ""
    refresh_success: bool = False
    total_cost: float = 0.0
    label: str = "pending_review"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "trigger_reason": self.trigger_reason,
            "steps": [step.to_dict() for step in self.steps],
            "diagnosed_cause": self.diagnosed_cause,
            "expected_cause": self.expected_cause,
            "recommendation": self.recommendation,
            "refresh_success": self.refresh_success,
            "total_cost": round(self.total_cost, 3),
            "rounds": len(self.steps),
            "label": self.label,
        }
