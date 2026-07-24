"""反欺诈 GNN 效果衰退诊断与候选刷新闭环。"""

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from src.llm import get_llm

from .memory import RefreshMemory, RefreshRetrieval
from .model_lab import DIAGNOSIS_ACTIONS, SimulatedGNNModelLab
from .policy import RefreshLLMPolicy, RefreshMockPolicy
from .rule_stream import ModelRefreshRuleStream
from .state import RefreshAction, RefreshState, RefreshStep, RefreshTrajectory


@dataclass
class ModelRefreshConfig:
    mode: str = "baseline"
    max_rounds: int = 10
    max_retries: int = 2
    initial_budget: float = 10.0
    max_experiments: int = 3
    log_verbose: bool = True

    @property
    def use_retrieval(self) -> bool:
        return self.mode in {"retrieval", "dpo_retrieval", "full"}


class ModelRefreshOrchestrator:
    def __init__(self, config: ModelRefreshConfig | None = None,
                 memory: RefreshMemory | None = None, lab=None):
        self.config = config or ModelRefreshConfig()
        self.memory = memory or RefreshMemory()
        self.retrieval = RefreshRetrieval(self.memory)
        self.rules = ModelRefreshRuleStream()
        self.lab = lab or SimulatedGNNModelLab()
        self.policy = (RefreshMockPolicy() if os.environ.get("LLM_MODEL", "mock") == "mock"
                       else RefreshLLMPolicy(get_llm()))

    def refresh(self, event: dict) -> RefreshTrajectory:
        state = RefreshState(
            event_id=event["event_id"],
            model_version=event["model_version"],
            baseline_metrics=deepcopy(event["baseline_metrics"]),
            current_metrics=deepcopy(event["current_metrics"]),
            drift_signals=deepcopy(event["drift_signals"]),
            segment_degradation=deepcopy(event["segment_degradation"]),
            label_context=deepcopy(event["label_context"]),
            remaining_budget=self.config.initial_budget,
            remaining_experiments=self.config.max_experiments,
        )
        traj = RefreshTrajectory(
            event_id=event["event_id"],
            trigger_reason=event["trigger_reason"],
            expected_cause=event["root_cause"],
        )
        error = None
        for round_num in range(1, self.config.max_rounds + 1):
            state.round_num = round_num
            retrieved = self.retrieval.search(state) if self.config.use_retrieval else []
            state.retrieval_confidence = retrieved[0]["similarity"] if retrieved else 0.0

            action = None
            for _ in range(self.config.max_retries + 1):
                try:
                    proposed = self.policy.propose(state, retrieved, error)
                except (ValueError, KeyError, json.JSONDecodeError) as exc:
                    error = f"INVALID_ACTION: {exc}"
                    continue
                violation = self.rules.validate(proposed, state)
                if violation is None:
                    action = proposed
                    break
                error = f"{violation.rule_name}: {violation.message}"
            if action is None:
                traj.recommendation = "human_review"
                break

            outcome = self.lab.execute(action, state, event)
            traj.steps.append(RefreshStep(deepcopy(state), action, outcome))
            traj.total_cost += outcome.cost
            self._update_state(state, action, outcome)
            error = None

            if self.config.log_verbose:
                print(f"[{event['event_id']} R{round_num}] {action.action_type} "
                      f"success={outcome.success} budget={state.remaining_budget:.1f}")

            if action.action_type in {"terminate", "recommend_rollback", "escalate_to_human"}:
                traj.recommendation = action.params.get(
                    "recommendation", "rollback" if action.action_type == "recommend_rollback" else "human_review"
                )
                break

        traj.diagnosed_cause = self._diagnosed_cause(state)
        expected_recommendation = event.get("expected_recommendation", "shadow_deploy")
        traj.refresh_success = bool(
            traj.diagnosed_cause == event["root_cause"]
            and traj.recommendation == expected_recommendation
        )
        traj.label = "accepted" if traj.refresh_success else "rejected"
        self.memory.save(traj)
        return traj

    @staticmethod
    def _update_state(state: RefreshState, action: RefreshAction, outcome) -> None:
        state.remaining_budget = round(state.remaining_budget - outcome.cost, 3)
        if action.action_type == "fine_tune_gnn":
            state.remaining_experiments -= 1
        state.action_history.append({
            "action_type": action.action_type,
            "success": outcome.success,
            "note": outcome.note,
        })
        if not outcome.success:
            return
        if action.action_type in DIAGNOSIS_ACTIONS:
            state.diagnosis[action.action_type] = deepcopy(outcome.metrics)
        elif action.action_type in {
            "adjust_training_window", "reweight_mature_samples", "mine_hard_negatives",
            "add_graph_relation_features", "repair_data_pipeline",
        }:
            state.interventions.append(action.action_type)
            if outcome.metrics.get("targeted"):
                state.diagnosis["targeted_root_cause"] = outcome.metrics.get("root_cause_hint")
        elif action.action_type == "fine_tune_gnn":
            state.candidate_metrics = deepcopy(outcome.metrics)
        elif action.action_type in {"run_out_of_time_test", "run_shadow_evaluation"}:
            state.validation.update(outcome.metrics)

    @staticmethod
    def _diagnosed_cause(state: RefreshState) -> str:
        if state.diagnosis.get("targeted_root_cause"):
            return state.diagnosis["targeted_root_cause"]
        scored = []
        for findings in state.diagnosis.values():
            if isinstance(findings, dict) and findings.get("cause"):
                scored.append((float(findings.get("confidence", 0)), findings["cause"]))
        return max(scored, default=(0.0, "unknown"))[1]
