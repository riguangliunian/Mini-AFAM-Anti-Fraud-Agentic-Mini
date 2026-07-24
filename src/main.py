"""
端到端调查 runner。

用法:
  # 跑单个告警
  python -m src.main --alert alert_000

  # 跑所有告警
  python -m src.main --all

  # 使用 mock LLM(默认)
  LLM_MODEL=mock python -m src.main --all

  # 使用真实 API
  LLM_MODEL=gpt-4o-mini OPENAI_API_KEY=xxx python -m src.main --alert alert_000
"""

import argparse
import json
from pathlib import Path

from .orchestrator import Orchestrator, OrchestratorConfig

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_alerts() -> list[dict]:
    with open(DATA_DIR / "alerts.json") as f:
        return json.load(f)


def _print_traj(traj):
    print("\n" + "=" * 70)
    print(f"Alert: {traj.alert_id}   Verdict: {traj.verdict}   "
          f"Confidence: {traj.final_confidence:.2f}   "
          f"Rounds: {len(traj.steps)}   Time: {traj.total_seconds:.1f}s")
    print("=" * 70)
    for i, step in enumerate(traj.steps, 1):
        act = step.action
        out = step.outcome
        print(f"\n[Round {i}] {act.action_type}({', '.join(f'{k}={v}' for k,v in act.params.items() if k != 'seeds' or len(str(v))<80)})")
        if act.rationale:
            print(f"  rationale: {act.rationale}")
        # 关键 metrics 显示
        interesting = {k: v for k, v in out.metrics.items()
                        if k not in ("_rule_obj",) and not k.startswith("_")}
        print(f"  outcome: {out.note}")
        for k, v in list(interesting.items())[:6]:
            print(f"    {k}: {v}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alert", type=str, help="specific alert_id")
    parser.add_argument("--all", action="store_true", help="run all alerts")
    parser.add_argument("--rounds", type=int, default=8, help="max rounds")
    parser.add_argument("--no-retrieval", action="store_true")
    parser.add_argument("--no-alignment", action="store_true")
    parser.add_argument("--no-rules", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="suppress internal logs")
    args = parser.parse_args()

    alerts = _load_alerts()
    if args.alert:
        alerts = [a for a in alerts if a["alert_id"] == args.alert]
        if not alerts:
            print(f"No alert with id {args.alert}. Available:")
            for a in _load_alerts():
                print(f"  - {a['alert_id']}: {a['trigger_reason']}")
            return
    elif not args.all:
        # 默认跑第一个
        alerts = alerts[:1]

    config = OrchestratorConfig(
        max_rounds=args.rounds,
        use_retrieval=not args.no_retrieval,
        use_alignment=not args.no_alignment,
        use_rules=not args.no_rules,
        log_verbose=not args.quiet,
    )
    orch = Orchestrator(config=config)

    for alert in alerts:
        print(f"\n\n########## Investigating {alert['alert_id']}: {alert['trigger_reason']} ##########")
        traj = orch.investigate(alert)
        _print_traj(traj)


if __name__ == "__main__":
    main()
