"""评测模型衰退诊断与GNN刷新Agent。"""

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from tabulate import tabulate

from src.model_refresh.memory import RefreshMemory
from src.model_refresh.orchestrator import ModelRefreshConfig, ModelRefreshOrchestrator


ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "model_refresh" / "eval_events.json"
LOGS_DIR = ROOT / "logs"


def run(mode: str, limit: int | None = None) -> tuple[list, str]:
    events = json.loads(DATA_PATH.read_text())["events"]
    if limit:
        events = events[:limit]
    path = LOGS_DIR / f"refresh_eval_memory_{mode}.jsonl"
    if path.exists():
        path.unlink()
    memory = RefreshMemory(path=path, index_writes=False)
    orch = ModelRefreshOrchestrator(ModelRefreshConfig(mode=mode, log_verbose=False), memory=memory)
    trajectories = [orch.refresh(event) for event in events]
    return trajectories, format_report(trajectories, mode)


def format_report(trajectories: list, mode: str) -> str:
    n = len(trajectories) or 1
    diagnosis_acc = sum(t.diagnosed_cause == t.expected_cause for t in trajectories) / n
    success = sum(t.refresh_success for t in trajectories) / n
    avg_rounds = sum(len(t.steps) for t in trajectories) / n
    avg_cost = sum(t.total_cost for t in trajectories) / n
    unnecessary_retrains = sum(
        any(s.action.action_type == "fine_tune_gnn" for s in t.steps)
        and not any(s.outcome.metrics.get("targeted_fix") for s in t.steps)
        for t in trajectories
    ) / n
    violations = sum(
        any(not s.outcome.success for s in t.steps) for t in trajectories
    ) / n
    lines = [f"# GNN Model Refresh Agent — {mode}", "", "## Summary", ""]
    lines.append(tabulate([
        ["Events", len(trajectories)],
        ["Root-cause accuracy", f"{diagnosis_acc:.1%}"],
        ["End-to-end refresh success", f"{success:.1%}"],
        ["Average rounds", f"{avg_rounds:.1f}"],
        ["Average budget cost", f"{avg_cost:.2f}"],
        ["Unnecessary retrain rate", f"{unnecessary_retrains:.1%}"],
        ["Tool failure trajectory rate", f"{violations:.1%}"],
    ], headers=["Metric", "Value"], tablefmt="github"))
    lines.extend(["", "## Per event", ""])
    rows = [[
        t.event_id, t.expected_cause, t.diagnosed_cause, t.recommendation,
        "yes" if t.refresh_success else "no", len(t.steps), f"{t.total_cost:.2f}",
    ] for t in trajectories]
    lines.append(tabulate(rows, headers=["Event", "Expected", "Diagnosed", "Recommendation",
                                           "Success", "Rounds", "Cost"], tablefmt="github"))
    by_cause = defaultdict(list)
    for t in trajectories:
        by_cause[t.expected_cause].append(t)
    lines.extend(["", "## Per drift type", ""])
    lines.append(tabulate([
        [cause, len(items), f"{sum(t.refresh_success for t in items)/len(items):.1%}"]
        for cause, items in sorted(by_cause.items())
    ], headers=["Drift type", "N", "Refresh success"], tablefmt="github"))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="+", default=["baseline"],
                        choices=["baseline", "retrieval", "dpo", "dpo_retrieval", "full"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-prefix", default="refresh_eval")
    args = parser.parse_args()
    for mode in args.modes:
        trajectories, report = run(mode, args.limit)
        tag = os.environ.get("LLM_MODEL", "mock").replace("/", "-").replace(":", "-")
        path = LOGS_DIR / f"{args.output_prefix}_{tag}_{mode}.md"
        path.write_text(report)
        print(report)
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
