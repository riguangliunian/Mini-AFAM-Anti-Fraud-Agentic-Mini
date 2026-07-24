"""模型刷新专用硬护栏。"""

from dataclasses import dataclass

from .state import RefreshAction, RefreshState


@dataclass
class RefreshViolation:
    rule_name: str
    message: str


class ModelRefreshRuleStream:
    MAX_FP_RATE = 0.005
    MIN_MATURE_LABEL_RATIO = 0.5
    MIN_RECALL_GAIN = 0.02

    def validate(self, action: RefreshAction, state: RefreshState) -> RefreshViolation | None:
        if action.cost > state.remaining_budget:
            return RefreshViolation("BUDGET_EXCEEDED", "Action cost exceeds remaining GPU/tool budget.")
        if action.action_type == "fine_tune_gnn":
            if not state.interventions:
                return RefreshViolation(
                    "BLIND_RETRAIN",
                    "Diagnose drift and select a targeted intervention before retraining."
                )
            maturity = state.label_context.get("positive_label_maturity", 1.0)
            if maturity < self.MIN_MATURE_LABEL_RATIO and "reweight_mature_samples" not in state.interventions:
                return RefreshViolation(
                    "IMMATURE_LABELS",
                    "Low label maturity requires maturity-aware reweighting before training."
                )
        if action.action_type == "run_out_of_time_test" and not state.candidate_metrics:
            return RefreshViolation("NO_CANDIDATE", "Train or repair a candidate before OOT validation.")
        if action.action_type == "run_shadow_evaluation" and "oot_passed" not in state.validation:
            return RefreshViolation("OOT_REQUIRED", "Out-of-time validation must run before shadow evaluation.")
        if action.action_type == "terminate" and action.params.get("recommendation") == "shadow_deploy":
            if not state.validation.get("shadow_passed", False):
                return RefreshViolation("SHADOW_REQUIRED", "Candidate cannot deploy before shadow passes.")
            if state.candidate_metrics.get("fp_rate", 1.0) > self.MAX_FP_RATE:
                return RefreshViolation("FP_GUARD", "Candidate false-positive rate exceeds production guardrail.")
            gain = (state.candidate_metrics.get("recall_at_fpr", 0.0)
                    - state.current_metrics.get("recall_at_fpr", 0.0))
            if gain < self.MIN_RECALL_GAIN:
                return RefreshViolation("NO_MATERIAL_GAIN", "Candidate has no material recall improvement.")
        return None
