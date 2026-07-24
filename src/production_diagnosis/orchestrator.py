"""State + Planner + Tool + Evaluation loop for production diagnosis."""

import json
import os
from copy import deepcopy
from dataclasses import dataclass

from src.llm import get_llm

from .memory import DiagnosisMemory, DiagnosisRetrieval
from .policy import DiagnosisLLMPolicy, DiagnosisMockPolicy
from .rule_stream import DiagnosisRuleStream
from .state import (
    DiagnosisAction,
    DiagnosisState,
    DiagnosisStep,
    DiagnosisTrajectory,
)
from .tool_lab import DIAGNOSIS_ACTIONS, SimulatedDiagnosisToolLab


@dataclass
class DiagnosisConfig:
    mode: str = "baseline"
    max_rounds: int = 10
    max_retries: int = 2
    initial_budget: float = 10.0
    log_verbose: bool = True

    @property
    def use_retrieval(self) -> bool:
        return self.mode in {"retrieval", "dpo_retrieval", "full"}


class DiagnosisOrchestrator:
    def __init__(self, config: DiagnosisConfig | None = None,
                 memory: DiagnosisMemory | None = None, tool_lab=None):
        self.config = config or DiagnosisConfig()
        self.memory = memory or DiagnosisMemory()
        self.retrieval = DiagnosisRetrieval(self.memory)
        self.rules = DiagnosisRuleStream()
        self.tool_lab = tool_lab or SimulatedDiagnosisToolLab()
        self.policy = (DiagnosisMockPolicy() if os.environ.get("LLM_MODEL", "mock") == "mock"
                       else DiagnosisLLMPolicy(get_llm()))

    def diagnose(self, event: dict) -> DiagnosisTrajectory:
        state = DiagnosisState(
            alert_id=event["alert_id"],
            model_name=event["model_name"],
            model_version=event["model_version"],
            monitor_alert=deepcopy(event["monitor_alert"]),
            metric_drop=deepcopy(event["metric_drop"]),
            affected_segments=deepcopy(event["affected_segments"]),
            remaining_budget=self.config.initial_budget,
        )
        traj = DiagnosisTrajectory(
            alert_id=event["alert_id"],
            trigger_reason=event["trigger_reason"],
            category=event.get("category", "uncategorized"),
            difficulty=event.get("difficulty", "unknown"),
            expected_root_cause=event["root_cause"],
            expected_repair=event["expected_repair"],
        )
        error = None
        for round_num in range(1, self.config.max_rounds + 1):
            state.round_num = round_num
            retrieved = self.retrieval.search(state) if self.config.use_retrieval else []
            state.retrieval_confidence = retrieved[0]["similarity"] if retrieved else 0.0

            action = self._next_valid_action(state, retrieved, error)
            if action is None:
                traj.repair_strategy = "human_review"
                break

            outcome = self.tool_lab.execute(action, state, event)
            traj.steps.append(DiagnosisStep(deepcopy(state), action, outcome))
            traj.total_cost += outcome.cost
            self._update_state(state, action, outcome)
            error = None

            if self.config.log_verbose:
                print(f"[{event['alert_id']} R{round_num}] {action.action_type} "
                      f"success={outcome.success} budget={state.remaining_budget:.1f}")

            if action.action_type in {"terminate", "escalate_to_human"}:
                traj.repair_strategy = (
                    action.params.get("repair_strategy")
                    or state.repair_candidate.get("strategy")
                    or "human_review"
                )
                break

        traj.diagnosed_root_cause = self._diagnosed_root_cause(state)
        if not traj.repair_strategy:
            traj.repair_strategy = state.repair_candidate.get("strategy", "human_review")
        traj.success = (
            traj.diagnosed_root_cause == event["root_cause"]
            and traj.repair_strategy == event["expected_repair"]
        )
        traj.label = "accepted" if traj.success else "rejected"
        self.memory.save(traj)
        return traj

    def _next_valid_action(self, state: DiagnosisState, retrieved: list[dict],
                           error: str | None) -> DiagnosisAction | None:
        last_error = error
        for _ in range(self.config.max_retries + 1):
            try:
                proposed = self.policy.propose(state, retrieved, last_error)
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                last_error = f"INVALID_ACTION: {exc}"
                continue
            violation = self.rules.validate(proposed, state)
            if violation is None:
                return proposed
            last_error = f"{violation.rule_name}: {violation.message}"
        return None

    @staticmethod
    def _update_state(state: DiagnosisState, action: DiagnosisAction, outcome) -> None:
        state.remaining_budget = round(state.remaining_budget - outcome.cost, 3)
        state.action_history.append({
            "action_type": action.action_type,
            "success": outcome.success,
            "note": outcome.note,
        })
        if not outcome.success:
            return
        metrics = deepcopy(outcome.metrics)
        if action.action_type in DIAGNOSIS_ACTIONS:
            DiagnosisOrchestrator._merge_diagnosis(state, action.action_type, metrics)
        elif action.action_type in {
            "propose_feature_patch", "adjust_threshold", "update_rule",
            "recommend_partial_retraining", "recommend_full_retraining",
        }:
            state.repair_candidate = deepcopy(metrics)
            if metrics.get("targeted"):
                state.hypotheses.append({
                    "cause": metrics.get("expected_root_cause"),
                    "confidence": 0.95,
                    "source": action.action_type,
                })
        elif action.action_type == "run_replay_backtest":
            state.replay = deepcopy(metrics)

    @staticmethod
    def _merge_diagnosis(state: DiagnosisState, action_type: str, metrics: dict) -> None:
        mapping = {
            "analyze_segment_drop": "affected_segments",
            "run_sql_profile": "sql_profile",
            "check_data_quality": "data_quality",
            "compute_feature_psi": "psi",
            "analyze_shap_shift": "shap",
            "analyze_behavior_sequence_shift": "behavior",
            "analyze_graph_pattern_shift": "graph",
            "check_label_maturity": "label_maturity",
        }
        setattr(state, mapping[action_type], metrics)
        if metrics.get("cause"):
            evidence = {
                "evidence_id": metrics.get("evidence_id"),
                "source": action_type,
                "cause": metrics["cause"],
                "severity": metrics.get("severity", "medium"),
                "summary": metrics.get("summary", ""),
            }
            state.evidence.append(evidence)
            state.hypotheses.append({
                "cause": metrics["cause"],
                "confidence": float(metrics.get("confidence", 0.6)),
                "source": action_type,
            })

    @staticmethod
    def _diagnosed_root_cause(state: DiagnosisState) -> str:
        scores: dict[str, float] = {}
        for hyp in state.hypotheses:
            cause = hyp.get("cause")
            if not cause:
                continue
            scores[cause] = max(scores.get(cause, 0.0), float(hyp.get("confidence", 0.0)))
        if not scores:
            return "unknown"
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)[0][0]
