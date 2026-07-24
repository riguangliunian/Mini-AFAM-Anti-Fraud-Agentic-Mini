"""运行模型刷新Agent：LLM_MODEL=mock python -m src.model_refresh.main。"""

import argparse
import json
from pathlib import Path

from .orchestrator import ModelRefreshConfig, ModelRefreshOrchestrator


DATA_PATH = Path(__file__).parents[2] / "data" / "model_refresh" / "eval_events.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", help="只运行指定event_id")
    parser.add_argument("--mode", default="baseline",
                        choices=["baseline", "retrieval", "dpo", "dpo_retrieval", "full"])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    events = json.loads(DATA_PATH.read_text())["events"]
    if args.event:
        events = [e for e in events if e["event_id"] == args.event]
    orch = ModelRefreshOrchestrator(ModelRefreshConfig(mode=args.mode, log_verbose=not args.quiet))
    for event in events:
        traj = orch.refresh(event)
        print(json.dumps({
            "event_id": traj.event_id,
            "expected": traj.expected_cause,
            "diagnosed": traj.diagnosed_cause,
            "recommendation": traj.recommendation,
            "success": traj.refresh_success,
            "rounds": len(traj.steps),
            "cost": traj.total_cost,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
