"""CLI runner for production fraud diagnosis."""

import argparse
import json
from pathlib import Path

from .orchestrator import DiagnosisConfig, DiagnosisOrchestrator


DATA_PATH = Path(__file__).parents[2] / "data" / "production_diagnosis" / "eval_events.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", help="Run one alert_id")
    parser.add_argument("--mode", default="baseline",
                        choices=["baseline", "retrieval", "dpo", "dpo_retrieval", "full"])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    events = json.loads(DATA_PATH.read_text())["events"]
    if args.event:
        events = [event for event in events if event["alert_id"] == args.event]
    orch = DiagnosisOrchestrator(DiagnosisConfig(mode=args.mode, log_verbose=not args.quiet))
    for event in events:
        traj = orch.diagnose(event)
        print(json.dumps({
            "alert_id": traj.alert_id,
            "expected_root_cause": traj.expected_root_cause,
            "diagnosed_root_cause": traj.diagnosed_root_cause,
            "expected_repair": traj.expected_repair,
            "repair_strategy": traj.repair_strategy,
            "success": traj.success,
            "rounds": len(traj.steps),
            "cost": round(traj.total_cost, 3),
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
