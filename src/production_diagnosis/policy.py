"""Planner policies for production fraud diagnosis."""

import json
import re

from .state import ACTION_SPECS, DiagnosisAction, DiagnosisState


class DiagnosisMockPolicy:
    def propose(self, state: DiagnosisState, retrieved: list[dict], error: str | None = None) -> DiagnosisAction:
        done = [item["action_type"] for item in state.action_history if item.get("success")]

        if error:
            if "REPLAY_REQUIRED" in error and "run_replay_backtest" not in done:
                return self._a("run_replay_backtest", "Validate the candidate repair before production recommendation.")
            if "NO_ROOT_CAUSE_HYPOTHESIS" in error and "analyze_segment_drop" not in done:
                return self._a("analyze_segment_drop", "Localize the drop before proposing a repair.")
            if "FULL_RETRAINING_TOO_EARLY" in error:
                return self._a("analyze_shap_shift", "Check attribution before escalating to full retraining.")

        if "analyze_segment_drop" not in done:
            return self._a("analyze_segment_drop", "Identify affected segments before deeper diagnosis.")

        retrieved_action = self._next_retrieved_action(retrieved, done)
        if retrieved_action:
            return self._a(
                retrieved_action,
                "Follow the diagnostic order from the most similar accepted expert trajectory.",
            )

        top_cause, top_conf = self._top_hypothesis(state)
        if top_cause == "data_quality_issue" and "check_data_quality" not in done:
            if "run_sql_profile" not in done:
                return self._a("run_sql_profile", "Check upstream volume and joins before patching features.")
            return self._a("check_data_quality", "Confirm whether the feature pipeline is broken.")
        if top_cause == "label_delay" and "check_label_maturity" not in done:
            return self._a("check_label_maturity", "Validate whether labels are mature enough for repair decisions.")
        if "compute_feature_psi" not in done:
            return self._a("compute_feature_psi", "Measure feature distribution drift before repair.")
        if "analyze_shap_shift" not in done:
            return self._a("analyze_shap_shift", "Check attribution and calibration changes.")
        if top_cause in {"attack_pattern_drift", "rule_interaction_issue"}:
            if "analyze_behavior_sequence_shift" not in done:
                return self._a("analyze_behavior_sequence_shift", "Check behavior-sequence evidence.")
            if "analyze_graph_pattern_shift" not in done:
                return self._a("analyze_graph_pattern_shift", "Check graph-pattern evidence.")

        top_cause, top_conf = self._top_hypothesis(state)
        if top_cause == "label_delay" and top_conf >= 0.75:
            return DiagnosisAction(
                "terminate",
                {"repair_strategy": "defer_until_label_mature"},
                "Stop automatic repair until labels mature.",
            )
        if not state.repair_candidate:
            repair_action = {
                "data_quality_issue": "propose_feature_patch",
                "feature_distribution_drift": "recommend_partial_retraining",
                "traffic_segment_shift": "adjust_threshold",
                "threshold_miscalibration": "adjust_threshold",
                "attack_pattern_drift": "update_rule",
                "rule_interaction_issue": "update_rule",
                "model_capacity_issue": "recommend_full_retraining",
            }.get(top_cause, "escalate_to_human")
            if repair_action == "escalate_to_human":
                return DiagnosisAction("escalate_to_human", {"reason": "no stable root-cause hypothesis"}, "")
            return self._a(repair_action, f"Select repair based on current top hypothesis: {top_cause}.")

        if "run_replay_backtest" not in done:
            return self._a("run_replay_backtest", "Replay the proposed repair on recent production traffic.")
        return DiagnosisAction(
            "terminate",
            {"repair_strategy": state.repair_candidate.get("strategy", "human_review")},
            "Finish with the validated repair recommendation.",
        )

    @staticmethod
    def _a(action_type: str, rationale: str) -> DiagnosisAction:
        return DiagnosisAction(action_type, {}, rationale)

    @staticmethod
    def _top_hypothesis(state: DiagnosisState) -> tuple[str, float]:
        scores: dict[str, float] = {}
        for item in state.hypotheses:
            cause = item.get("cause")
            if cause:
                scores[cause] = max(scores.get(cause, 0.0), float(item.get("confidence", 0.0)))
        if not scores:
            return "unknown", 0.0
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[0]

    @staticmethod
    def _next_retrieved_action(retrieved: list[dict], done: list[str]) -> str | None:
        if not retrieved:
            return None
        top = retrieved[0]
        if top.get("similarity", 0.0) < 0.55:
            return None
        actions = top.get("trajectory", {}).get("recommended_actions", [])
        for action in actions:
            if action not in done:
                return action
        return None


class DiagnosisLLMPolicy:
    def __init__(self, llm):
        self.llm = llm

    def propose(self, state: DiagnosisState, retrieved: list[dict], error: str | None = None) -> DiagnosisAction:
        allowed_actions = {
            action: {
                "kind": spec["kind"],
                "params": self._params_for_action(action),
            }
            for action, spec in ACTION_SPECS.items()
        }
        prompt = {
            "state": state.to_prompt_dict(),
            "retrieved_expert_trajectories": [
                {
                    "similarity": round(item["similarity"], 3),
                    "root_cause": item["trajectory"].get("diagnosed_root_cause"),
                    "repair_strategy": item["trajectory"].get("repair_strategy"),
                }
                for item in retrieved
            ],
            "previous_validation_error": error,
            "allowed_actions": allowed_actions,
            "required_output_schema": {
                "action_type": "one of allowed_actions keys",
                "params": "object, may be empty unless terminal/repair action needs a strategy",
                "rationale": "short evidence-based reason",
            },
        }
        system = (
            "You are a senior fraud algorithm engineer diagnosing a production model alert. "
            "Choose exactly one allowed JSON action. Collect evidence before repair, validate "
            "repairs with replay, avoid unnecessary full retraining, and stop when evidence is sufficient. "
            "Return only a JSON object with keys action_type, params, rationale. No markdown, no prose."
        )
        raw = self.llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ])
        obj = self._parse_json(raw)
        return DiagnosisAction(obj["action_type"], obj.get("params", {}), obj.get("rationale", ""))

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw or "", re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _params_for_action(action_type: str) -> dict:
        if action_type == "terminate":
            return {"repair_strategy": "one of feature_patch, threshold_adjustment, rule_update, partial_retraining, full_retraining, defer_until_label_mature, human_review"}
        if action_type == "escalate_to_human":
            return {"reason": "short reason"}
        return {}
