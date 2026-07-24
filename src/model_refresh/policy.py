"""模型刷新策略：真实LLM JSON Action与可复现Mock策略。"""

import json

from .state import RefreshAction, RefreshState


class RefreshMockPolicy:
    """根据可观察漂移信号决策，不直接读取隐藏root_cause。"""

    def propose(self, state: RefreshState, retrieved: list[dict], error: str | None = None) -> RefreshAction:
        done = [x["action_type"] for x in state.action_history if x.get("success")]
        sig = state.drift_signals

        if error:
            if "IMMATURE_LABELS" in error and "reweight_mature_samples" not in done:
                return self._a("reweight_mature_samples", "Use only mature/reliable labels.")
            if "SHADOW_REQUIRED" in error and "run_shadow_evaluation" not in done:
                return self._a("run_shadow_evaluation", "Complete shadow validation.")
            if "BLIND_RETRAIN" in error:
                return self._a("analyze_feature_drift", "Diagnose before retraining.")

        if "analyze_segment_performance" not in done:
            return self._a("analyze_segment_performance", "Localize degradation before changing the model.")

        # 数据缺失突变优先排查管道，防止把数据故障误判为概念漂移。
        if sig.get("missing_rate_change", 0) >= 0.15:
            if "analyze_feature_drift" not in done:
                return self._a("analyze_feature_drift", "Large missing-rate jump may indicate pipeline failure.")
            if "repair_data_pipeline" not in done:
                return self._a("repair_data_pipeline", "Repair the confirmed data pipeline anomaly.")
        elif state.label_context.get("positive_label_maturity", 1) < 0.5:
            if "analyze_label_maturity" not in done:
                return self._a("analyze_label_maturity", "Verify whether apparent degradation is label delay.")
            if "reweight_mature_samples" not in done:
                return self._a("reweight_mature_samples", "Weight training by label maturity.")
        elif max(sig.get("edge_type_psi", 0), sig.get("degree_shift", 0), sig.get("embedding_mmd", 0)) >= 0.18:
            if "analyze_graph_drift" not in done:
                return self._a("analyze_graph_drift", "Graph topology shifted materially.")
            if "inspect_false_negative_clusters" not in done:
                return self._a("inspect_false_negative_clusters", "Find the new missed graph pattern.")
            if "add_graph_relation_features" not in done:
                return self._a("add_graph_relation_features", "Add relations matching the missed attack structure.")
        elif sig.get("node_feature_psi", 0) >= 0.18:
            if "analyze_feature_drift" not in done:
                return self._a("analyze_feature_drift", "Node feature drift is the dominant signal.")
            if "adjust_training_window" not in done:
                return self._a("adjust_training_window", "Use a recent window to match current behavior.")
        else:
            if "inspect_false_positive_clusters" not in done:
                return self._a("inspect_false_positive_clusters", "Inspect hard normal clusters and segment shift.")
            if "mine_hard_negatives" not in done:
                return self._a("mine_hard_negatives", "Add confusing normal traffic as hard negatives.")

        if "fine_tune_gnn" not in done:
            return self._a("fine_tune_gnn", "Train one targeted candidate within budget.")
        if "run_out_of_time_test" not in done:
            return self._a("run_out_of_time_test", "Validate on a future, label-mature time window.")
        if not state.validation.get("oot_passed", False):
            return RefreshAction("recommend_rollback", {"reason": "candidate_failed_oot"},
                                 "Do not deploy a candidate that fails OOT.")
        if "run_shadow_evaluation" not in done:
            return self._a("run_shadow_evaluation", "Compare candidate on shadow traffic.")
        recommendation = "shadow_deploy" if state.validation.get("shadow_passed") else "keep_champion"
        return RefreshAction("terminate", {"recommendation": recommendation},
                             "Finish with an auditable deployment recommendation.")

    @staticmethod
    def _a(action_type: str, rationale: str) -> RefreshAction:
        return RefreshAction(action_type, {}, rationale)


class RefreshLLMPolicy:
    def __init__(self, llm):
        self.llm = llm

    def propose(self, state: RefreshState, retrieved: list[dict], error: str | None = None) -> RefreshAction:
        examples = [{
            "similarity": round(x["similarity"], 3),
            "diagnosed_cause": x["trajectory"].get("diagnosed_cause"),
            "recommendation": x["trajectory"].get("recommendation"),
        } for x in retrieved]
        prompt = {
            "state": state.to_prompt_dict(),
            "retrieved_successful_refreshes": examples,
            "previous_validation_error": error,
        }
        system = """You orchestrate maintenance of a production fraud GNN.
Choose exactly one allowed action. Diagnose before retraining, optimize recall at a fixed
false-positive rate, account for delayed labels and budget, and never deploy without OOT
and shadow validation. Return JSON with action_type, params, rationale only."""
        raw = self.llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ])
        obj = json.loads(raw)
        return RefreshAction(obj["action_type"], obj.get("params", {}), obj.get("rationale", ""))
