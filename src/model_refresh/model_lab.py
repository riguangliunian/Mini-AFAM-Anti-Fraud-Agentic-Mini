"""可替换的 GNN ModelLab。

当前实现为确定性模拟器，真实接入时只需保持 execute(action, state, event)
返回 RefreshOutcome 的接口不变。
"""

from copy import deepcopy

from .state import RefreshAction, RefreshOutcome, RefreshState


DIAGNOSIS_ACTIONS = {
    "analyze_segment_performance": "segment_shift",
    "analyze_feature_drift": "feature_or_pipeline",
    "analyze_graph_drift": "graph_shift",
    "analyze_label_maturity": "label_delay",
    "inspect_false_negative_clusters": "missed_attack_pattern",
    "inspect_false_positive_clusters": "false_positive_shift",
}


class SimulatedGNNModelLab:
    """由隐藏root_cause和修复动作共同决定候选模型效果。"""

    def execute(self, action: RefreshAction, state: RefreshState, event: dict) -> RefreshOutcome:
        t = action.action_type
        cost = action.cost
        root = event["root_cause"]

        if t in DIAGNOSIS_ACTIONS:
            findings = event.get("findings", {}).get(t, {})
            return RefreshOutcome(True, findings, f"diagnostic completed: {t}", cost)

        if t in {
            "adjust_training_window", "reweight_mature_samples", "mine_hard_negatives",
            "add_graph_relation_features", "repair_data_pipeline",
        }:
            expected = event.get("best_intervention") == t
            return RefreshOutcome(
                True,
                {"targeted": expected, "root_cause_hint": root if expected else "inconclusive"},
                f"registered intervention {t}",
                cost,
            )

        if t == "fine_tune_gnn":
            current = state.current_metrics
            best = event.get("best_intervention")
            targeted = best in state.interventions
            gain = event.get("targeted_gain", 0.10) if targeted else event.get("generic_gain", 0.005)
            fp_delta = event.get("targeted_fp_delta", 0.0001) if targeted else 0.001
            metrics = deepcopy(current)
            metrics["recall_at_fpr"] = round(min(0.99, current["recall_at_fpr"] + gain), 4)
            metrics["pr_auc"] = round(min(0.99, current["pr_auc"] + gain * 0.65), 4)
            metrics["amount_recall"] = round(min(0.99, current["amount_recall"] + gain * 0.8), 4)
            metrics["fp_rate"] = round(max(0.0, current["fp_rate"] + fp_delta), 5)
            metrics["targeted_fix"] = targeted
            return RefreshOutcome(True, metrics, "candidate GNN training completed", cost)

        if t == "run_out_of_time_test":
            cm = state.candidate_metrics
            gain = cm.get("recall_at_fpr", 0) - state.current_metrics.get("recall_at_fpr", 0)
            passed = gain >= 0.02 and cm.get("fp_rate", 1) <= 0.005
            return RefreshOutcome(True, {"oot_passed": passed, "recall_gain": round(gain, 4)},
                                  "OOT evaluation completed", cost)

        if t == "run_shadow_evaluation":
            passed = bool(state.validation.get("oot_passed")) and state.candidate_metrics.get("targeted_fix", False)
            return RefreshOutcome(True, {"shadow_passed": passed, "traffic_fraction": 0.05},
                                  "shadow evaluation completed", cost)

        if t in {"terminate", "recommend_rollback", "escalate_to_human"}:
            return RefreshOutcome(True, action.params, t, cost)

        return RefreshOutcome(False, {"error": "unsupported_action"}, t, cost)
