"""Hard guards for diagnosis and repair planning."""

from dataclasses import dataclass

from .state import DiagnosisAction, DiagnosisState


@dataclass
class DiagnosisViolation:
    rule_name: str
    message: str


class DiagnosisRuleStream:
    MAX_FP_RATE = 0.005
    MIN_REPLAY_GAIN = 0.02

    def validate(self, action: DiagnosisAction, state: DiagnosisState) -> DiagnosisViolation | None:
        if action.cost > state.remaining_budget:
            return DiagnosisViolation("BUDGET_EXCEEDED", "Action cost exceeds remaining diagnosis budget.")

        if action.action_type in {
            "propose_feature_patch", "adjust_threshold", "update_rule",
            "recommend_partial_retraining", "recommend_full_retraining",
        }:
            if not state.hypotheses:
                return DiagnosisViolation("NO_ROOT_CAUSE_HYPOTHESIS", "Collect evidence before proposing a repair.")

        if action.action_type == "recommend_full_retraining":
            if not self._has_evidence(state, "model_capacity_issue"):
                return DiagnosisViolation(
                    "FULL_RETRAINING_TOO_EARLY",
                    "Full retraining requires evidence that lighter repairs are insufficient.",
                )

        if action.action_type == "adjust_threshold":
            if not (self._has_evidence(state, "threshold_miscalibration")
                    or self._has_evidence(state, "traffic_segment_shift")):
                return DiagnosisViolation(
                    "THRESHOLD_WITHOUT_CALIBRATION",
                    "Threshold change requires calibration or segment-shift evidence.",
                )

        if action.action_type == "update_rule":
            if not (self._has_evidence(state, "attack_pattern_drift")
                    or self._has_evidence(state, "rule_interaction_issue")):
                return DiagnosisViolation("RULE_WITHOUT_RULE_OR_ATTACK_EVIDENCE", "Rule update needs rule or attack evidence.")

        if action.action_type == "run_replay_backtest" and not state.repair_candidate:
            return DiagnosisViolation("NO_REPAIR_CANDIDATE", "Replay requires a concrete repair candidate.")

        if action.action_type == "terminate":
            recommendation = action.params.get("repair_strategy") or state.repair_candidate.get("strategy")
            if recommendation and recommendation not in {"human_review", "defer_until_label_mature"}:
                if not state.replay.get("passed", False):
                    return DiagnosisViolation("REPLAY_REQUIRED", "Production repair recommendation requires passing replay.")
                if state.replay.get("fp_rate", 1.0) > self.MAX_FP_RATE:
                    return DiagnosisViolation("FP_GUARD", "Replay false-positive rate exceeds guardrail.")
                if state.replay.get("metric_gain", 0.0) < self.MIN_REPLAY_GAIN:
                    return DiagnosisViolation("NO_MATERIAL_GAIN", "Replay gain is too small for production change.")

        return None

    @staticmethod
    def _has_evidence(state: DiagnosisState, cause: str) -> bool:
        return any(item.get("cause") == cause for item in state.evidence)
