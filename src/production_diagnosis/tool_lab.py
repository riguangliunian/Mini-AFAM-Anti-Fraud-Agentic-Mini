"""Replaceable tool layer for production fraud diagnosis.

The default implementation is deterministic and data-driven. In production, each
action can be wired to SQL, PSI jobs, SHAP analysis, behavior sequence analysis,
graph mining, or replay services while preserving the same outcome shape.
"""

from .state import DiagnosisAction, DiagnosisOutcome, DiagnosisState


DIAGNOSIS_ACTIONS = {
    "analyze_segment_drop",
    "run_sql_profile",
    "check_data_quality",
    "compute_feature_psi",
    "analyze_shap_shift",
    "analyze_behavior_sequence_shift",
    "analyze_graph_pattern_shift",
    "check_label_maturity",
}

REPAIR_TO_ACTION = {
    "feature_patch": "propose_feature_patch",
    "threshold_adjustment": "adjust_threshold",
    "rule_update": "update_rule",
    "partial_retraining": "recommend_partial_retraining",
    "full_retraining": "recommend_full_retraining",
    "defer_until_label_mature": "terminate",
}


class SimulatedDiagnosisToolLab:
    def execute(self, action: DiagnosisAction, state: DiagnosisState, event: dict) -> DiagnosisOutcome:
        if action.action_type in DIAGNOSIS_ACTIONS:
            return self._diagnose(action, event)
        if action.action_type in {
            "propose_feature_patch", "adjust_threshold", "update_rule",
            "recommend_partial_retraining", "recommend_full_retraining",
        }:
            return self._repair(action, event)
        if action.action_type == "run_replay_backtest":
            return self._replay(state, event, action.cost)
        if action.action_type in {"terminate", "escalate_to_human"}:
            return DiagnosisOutcome(True, action.params, action.action_type, action.cost)
        return DiagnosisOutcome(False, {"error": "unsupported_action"}, action.action_type, action.cost)

    @staticmethod
    def _diagnose(action: DiagnosisAction, event: dict) -> DiagnosisOutcome:
        finding = event.get("tool_findings", {}).get(action.action_type, {})
        metrics = dict(finding)
        if metrics:
            metrics.setdefault("evidence_id", f"ev_{event['alert_id']}_{action.action_type}")
        return DiagnosisOutcome(True, metrics, f"completed {action.action_type}", action.cost)

    @staticmethod
    def _repair(action: DiagnosisAction, event: dict) -> DiagnosisOutcome:
        action_to_strategy = {
            "propose_feature_patch": "feature_patch",
            "adjust_threshold": "threshold_adjustment",
            "update_rule": "rule_update",
            "recommend_partial_retraining": "partial_retraining",
            "recommend_full_retraining": "full_retraining",
        }
        strategy = action_to_strategy[action.action_type]
        targeted = strategy == event["expected_repair"]
        return DiagnosisOutcome(
            True,
            {
                "strategy": strategy,
                "targeted": targeted,
                "expected_root_cause": event["root_cause"] if targeted else "inconclusive",
            },
            f"proposed {strategy}",
            action.cost,
        )

    @staticmethod
    def _replay(state: DiagnosisState, event: dict, cost: float) -> DiagnosisOutcome:
        strategy = state.repair_candidate.get("strategy", "unknown")
        targeted = strategy == event["expected_repair"]
        base_gain = event.get("expected_gain", 0.08)
        metric_gain = base_gain if targeted else event.get("generic_gain", 0.005)
        fp_rate = event.get("targeted_fp_rate", 0.0015) if targeted else event.get("generic_fp_rate", 0.006)
        passed = metric_gain >= 0.02 and fp_rate <= 0.005
        return DiagnosisOutcome(
            True,
            {
                "passed": passed,
                "strategy": strategy,
                "metric_gain": round(metric_gain, 4),
                "fp_rate": round(fp_rate, 5),
                "amount_recall_gain": round(metric_gain * 0.9, 4),
            },
            "replay backtest completed",
            cost,
        )
