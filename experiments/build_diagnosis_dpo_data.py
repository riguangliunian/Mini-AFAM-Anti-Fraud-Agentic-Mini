"""Build decision-level SFT/DPO pairs from expert-like diagnosis trajectories."""

import argparse
import json
import os
from pathlib import Path

from src.production_diagnosis.memory import DiagnosisMemory
from src.production_diagnosis.orchestrator import DiagnosisConfig, DiagnosisOrchestrator
from src.production_diagnosis.state import ACTION_SPECS


ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "production_diagnosis" / "eval_events.json"

REJECTED_BY_KIND = {
    "diagnosis": {
        "action_type": "recommend_full_retraining",
        "params": {},
        "rationale": "Retrain immediately before diagnosing the production alert.",
    },
    "repair": {
        "action_type": "recommend_full_retraining",
        "params": {},
        "rationale": "Use the most expensive repair without evidence that lighter options fail.",
    },
    "evaluation": {
        "action_type": "terminate",
        "params": {"repair_strategy": "partial_retraining"},
        "rationale": "Recommend production change without replay evidence.",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "logs" / "diagnosis_dpo_train.jsonl"))
    args = parser.parse_args()
    os.environ["LLM_MODEL"] = "mock"

    events = json.loads(DATA_PATH.read_text())["events"]
    source_memory = ROOT / "logs" / "diagnosis_dpo_source_memory.jsonl"
    if source_memory.exists():
        source_memory.unlink()
    orch = DiagnosisOrchestrator(
        DiagnosisConfig(mode="baseline", log_verbose=False),
        memory=DiagnosisMemory(source_memory, include_seed=False, index_writes=False),
    )
    pairs = []
    for event in events:
        traj = orch.diagnose(event)
        if not traj.success:
            continue
        for step in traj.steps:
            kind = ACTION_SPECS[step.action.action_type]["kind"]
            rejected = REJECTED_BY_KIND.get(kind)
            if not rejected or rejected["action_type"] == step.action.action_type:
                continue
            prompt = {
                "task": "Choose the next diagnostic action for a production fraud model alert.",
                "state": step.state.to_prompt_dict(),
                "allowed_actions": "See production_diagnosis ACTION_SPECS",
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
                "metadata": {
                    "alert_id": event["alert_id"],
                    "category": event.get("category", "uncategorized"),
                    "difficulty": event.get("difficulty", "unknown"),
                    "root_cause": event["root_cause"],
                    "expected_repair": event["expected_repair"],
                    "decision_kind": kind,
                },
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in pairs))
    print(f"Saved {len(pairs)} diagnosis decision preference pairs to {out}")


if __name__ == "__main__":
    main()
