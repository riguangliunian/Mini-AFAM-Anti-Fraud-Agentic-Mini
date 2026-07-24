"""从成功模型刷新轨迹生成决策点级DPO偏好对。"""

import argparse
import json
import os
from pathlib import Path

from src.model_refresh.memory import RefreshMemory
from src.model_refresh.orchestrator import ModelRefreshConfig, ModelRefreshOrchestrator


ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "model_refresh" / "eval_events.json"

REJECTED_BY_KIND = {
    "diagnosis": {"action_type": "fine_tune_gnn", "params": {},
                  "rationale": "Retrain immediately without diagnosing the degradation."},
    "intervention": {"action_type": "adjust_training_window", "params": {},
                     "rationale": "Apply a generic recent window regardless of root cause."},
    "training": {"action_type": "terminate", "params": {"recommendation": "shadow_deploy"},
                 "rationale": "Deploy the intervention without training and validating a candidate."},
    "validation": {"action_type": "terminate", "params": {"recommendation": "shadow_deploy"},
                   "rationale": "Deploy without completing required validation."},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "logs" / "refresh_dpo_train.jsonl"))
    args = parser.parse_args()
    os.environ["LLM_MODEL"] = "mock"
    events = json.loads(DATA_PATH.read_text())["events"]
    temp_memory = ROOT / "logs" / "refresh_dpo_source_memory.jsonl"
    if temp_memory.exists():
        temp_memory.unlink()
    orch = ModelRefreshOrchestrator(
        ModelRefreshConfig(mode="baseline", log_verbose=False),
        memory=RefreshMemory(temp_memory, include_seed=False, index_writes=False),
    )
    pairs = []
    for event in events:
        traj = orch.refresh(event)
        if not traj.refresh_success:
            continue
        for step in traj.steps:
            kind = _kind(step.action.action_type)
            rejected = REJECTED_BY_KIND.get(kind)
            if not rejected or rejected["action_type"] == step.action.action_type:
                continue
            prompt = {
                "task": "Choose the next action for production fraud GNN maintenance.",
                "state": step.state.to_prompt_dict(),
                "allowed_actions": "See model_refresh ACTION_SPECS",
            }
            chosen = {
                "action_type": step.action.action_type,
                "params": step.action.params,
                "rationale": step.action.rationale,
            }
            pairs.append({
                "prompt": json.dumps(prompt, ensure_ascii=False, sort_keys=True),
                "chosen": json.dumps(chosen, ensure_ascii=False, sort_keys=True),
                "rejected": json.dumps(rejected, ensure_ascii=False, sort_keys=True),
                "metadata": {"event_id": event["event_id"], "root_cause": event["root_cause"],
                             "decision_kind": kind},
            })
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs))
    print(f"Saved {len(pairs)} decision-level preference pairs to {out}")


def _kind(action_type: str) -> str:
    from src.model_refresh.state import ACTION_SPECS
    return ACTION_SPECS[action_type]["kind"]


if __name__ == "__main__":
    main()
