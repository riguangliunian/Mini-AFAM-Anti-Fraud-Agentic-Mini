"""Evaluate the production fraud diagnosis agent."""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from tabulate import tabulate

from src.production_diagnosis.memory import DiagnosisMemory
from src.production_diagnosis.orchestrator import DiagnosisConfig, DiagnosisOrchestrator


ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "production_diagnosis" / "eval_events.json"
LOGS_DIR = ROOT / "logs"


class AttrDict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def run(mode: str, limit: int | None = None,
        category: str | None = None,
        max_rounds: int = 10) -> tuple[list, str]:
    events = json.loads(DATA_PATH.read_text())["events"]
    if category:
        events = [event for event in events if event.get("category") == category]
    if limit:
        events = events[:limit]
    memory_path = LOGS_DIR / f"diagnosis_eval_memory_{mode}.jsonl"
    if memory_path.exists():
        memory_path.unlink()
    memory = DiagnosisMemory(path=memory_path, index_writes=False)
    orch = DiagnosisOrchestrator(
        DiagnosisConfig(mode=mode, max_rounds=max_rounds, log_verbose=False),
        memory=memory,
    )
    trajectories = []
    for idx, event in enumerate(events, start=1):
        print(f"[{mode}] {idx}/{len(events)} {event['alert_id']} ...", flush=True)
        traj = orch.diagnose(event)
        trajectories.append(traj)
        print(
            f"[{mode}] {event['alert_id']} cause={traj.diagnosed_root_cause} "
            f"repair={traj.repair_strategy} success={traj.success} "
            f"rounds={len(traj.steps)} cost={traj.total_cost:.2f}",
            flush=True,
        )
    event_map = {event["alert_id"]: event for event in events}
    return trajectories, format_report(trajectories, mode, category, event_map)


def load_from_memory(mode: str, category: str | None = None,
                     limit: int | None = None) -> tuple[list, str]:
    events = json.loads(DATA_PATH.read_text())["events"]
    if category:
        events = [event for event in events if event.get("category") == category]
    event_map = {event["alert_id"]: event for event in events}
    memory_path = LOGS_DIR / f"diagnosis_eval_memory_{mode}.jsonl"
    trajectories = []
    for line in memory_path.read_text().splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item["alert_id"] not in event_map:
            continue
        trajectories.append(_to_namespace(item))
        if limit and len(trajectories) >= limit:
            break
    return trajectories, format_report(trajectories, mode, category, event_map)


def format_report(trajectories: list, mode: str, category_filter: str | None = None,
                  event_map: dict | None = None) -> str:
    event_map = event_map or {}
    n = len(trajectories) or 1
    root_acc = sum(t.diagnosed_root_cause == t.expected_root_cause for t in trajectories) / n
    repair_acc = sum(t.repair_strategy == t.expected_repair for t in trajectories) / n
    joint_acc = sum(t.success for t in trajectories) / n
    avg_rounds = sum(len(t.steps) for t in trajectories) / n
    avg_cost = sum(t.total_cost for t in trajectories) / n
    replay_count = sum(any(s.action.action_type == "run_replay_backtest" for s in t.steps)
                       for t in trajectories)
    replay_pass = sum(any(s.action.action_type == "run_replay_backtest" and s.outcome.metrics.get("passed")
                          for s in t.steps) for t in trajectories)
    full_retrain = sum(t.repair_strategy == "full_retraining" for t in trajectories)
    unnecessary_full = sum(
        t.repair_strategy == "full_retraining" and t.expected_repair != "full_retraining"
        for t in trajectories
    )
    premature_fix = sum(
        t.repair_strategy not in {"human_review", "defer_until_label_mature"}
        and not any(s.action.action_type == "run_replay_backtest" for s in t.steps)
        for t in trajectories
    )
    process_scores = [_process_score(t, event_map.get(t.alert_id, {})) for t in trajectories]
    required_tool_recall = (
        sum(item["required_recall"] for item in process_scores) / len(process_scores)
        if process_scores else 1.0
    )
    forbidden_tool_rate = (
        sum(1 for item in process_scores if item["forbidden_called"]) / len(process_scores)
        if process_scores else 0.0
    )
    process_success = (
        sum(1 for item in process_scores if item["process_success"]) / len(process_scores)
        if process_scores else 1.0
    )
    overall_success = (
        sum(1 for t, item in zip(trajectories, process_scores) if t.success and item["process_success"]) / n
    )
    business_scores = [_business_score(t, event_map.get(t.alert_id, {})) for t in trajectories]
    fraud_scores = [_fraud_score(t, event_map.get(t.alert_id, {})) for t in trajectories]
    expected_metric_recovery = sum(item["metric_recovery"] for item in business_scores) / n
    recall_recovery = sum(item["recall_recovery"] for item in business_scores) / n
    stability_violation_rate = sum(1 for item in business_scores if item["stability_violation"]) / n
    coverage_loss = sum(item["coverage_loss"] for item in business_scores) / n
    false_positive_impact = sum(item["false_positive_impact"] for item in business_scores) / n
    review_workload_change = sum(item["review_workload_change"] for item in business_scores) / n
    repair_acceptance_rate = sum(1 for item in business_scores if item["accepted"]) / n
    handover_rate = sum(1 for item in business_scores if item["handover"]) / n
    fraud_recall_recovery = sum(item["fraud_recall_recovery"] for item in fraud_scores) / n
    amount_recall_recovery = sum(item["amount_recall_recovery"] for item in fraud_scores) / n
    segment_recovery = sum(item["segment_recovery"] for item in fraud_scores) / n
    safe_deployment_rate = sum(1 for item in fraud_scores if item["safe_deployment"]) / n
    time_to_mitigation = sum(item["time_to_mitigation_hours"] for item in fraud_scores) / n
    novel_cases = [item for item in fraud_scores if item["is_novel_attack_case"]]
    novel_attack_detection = (
        sum(1 for item in novel_cases if item["novel_attack_detected"]) / len(novel_cases)
        if novel_cases else 1.0
    )
    label_cases = [item for item in fraud_scores if item["is_label_maturity_case"]]
    label_maturity_guard = (
        sum(1 for item in label_cases if item["label_maturity_guard_ok"]) / len(label_cases)
        if label_cases else 1.0
    )
    rule_cases = [item for item in fraud_scores if item["is_rule_update_case"]]
    rule_robustness = (
        sum(item["rule_robustness"] for item in rule_cases) / len(rule_cases)
        if rule_cases else 1.0
    )

    lines = [f"# Production Fraud Diagnosis Agent - {mode}", "", "## Summary", ""]
    if category_filter:
        lines.insert(1, f"Category filter: `{category_filter}`")
        lines.insert(2, "")
    lines.append(tabulate([
        ["Events", len(trajectories)],
        ["Root-cause accuracy", f"{root_acc:.1%}"],
        ["Repair strategy accuracy", f"{repair_acc:.1%}"],
        ["Joint success", f"{joint_acc:.1%}"],
        ["Average rounds", f"{avg_rounds:.1f}"],
        ["Average tool cost", f"{avg_cost:.2f}"],
        ["Replay pass rate", f"{(replay_pass / replay_count):.1%}" if replay_count else "n/a"],
        ["Full retraining recommendations", full_retrain],
        ["Unnecessary full retraining rate", f"{(unnecessary_full / n):.1%}"],
        ["Premature fix rate", f"{(premature_fix / n):.1%}"],
        ["Required tool recall", f"{required_tool_recall:.1%}"],
        ["Forbidden tool trajectory rate", f"{forbidden_tool_rate:.1%}"],
        ["Process success", f"{process_success:.1%}"],
        ["Overall success incl. process", f"{overall_success:.1%}"],
    ], headers=["Metric", "Value"], tablefmt="github"))

    lines.extend(["", "## Business Refresh Metrics", ""])
    lines.append(tabulate([
        ["Expected metric recovery", f"{expected_metric_recovery:.1%}"],
        ["Recall recovery", f"{recall_recovery:.1%}"],
        ["Stability violation rate", f"{stability_violation_rate:.1%}"],
        ["Average coverage loss", f"{coverage_loss:.1%}"],
        ["False-positive impact", f"{false_positive_impact:.2%}"],
        ["Review workload change", f"{review_workload_change:+.1%}"],
        ["Repair acceptance rate", f"{repair_acceptance_rate:.1%}"],
        ["Human handover rate", f"{handover_rate:.1%}"],
    ], headers=["Business metric", "Value"], tablefmt="github"))

    lines.extend(["", "## Fraud-Specific Production Metrics", ""])
    lines.append(tabulate([
        ["Fraud recall recovery", f"{fraud_recall_recovery:.1%}"],
        ["Amount recall recovery", f"{amount_recall_recovery:.1%}"],
        ["Segment-level recovery", f"{segment_recovery:.1%}"],
        ["Novel attack detection rate", f"{novel_attack_detection:.1%}"],
        ["Label maturity guard accuracy", f"{label_maturity_guard:.1%}"],
        ["Rule robustness / bypass resistance", f"{rule_robustness:.1%}"],
        ["Safe deployment rate", f"{safe_deployment_rate:.1%}"],
        ["Avg time-to-mitigation", f"{time_to_mitigation:.1f}h"],
    ], headers=["Fraud metric", "Value"], tablefmt="github"))

    rows = []
    for t in trajectories:
        ps = _process_score(t, event_map.get(t.alert_id, {}))
        bs = _business_score(t, event_map.get(t.alert_id, {}))
        fs = _fraud_score(t, event_map.get(t.alert_id, {}))
        rows.append([
            t.alert_id,
            t.category,
            t.difficulty,
            t.expected_root_cause,
            t.diagnosed_root_cause,
            t.expected_repair,
            t.repair_strategy,
            "yes" if t.success else "no",
            "yes" if ps["process_success"] else "no",
            f"{bs['metric_recovery']:.1%}",
            "yes" if bs["accepted"] else "no",
            "yes" if fs["safe_deployment"] else "no",
            len(t.steps),
            f"{t.total_cost:.2f}",
        ])
    lines.extend(["", "## Per Event", ""])
    lines.append(tabulate(rows, headers=[
        "Alert", "Category", "Difficulty", "Expected cause", "Diagnosed cause", "Expected repair",
        "Repair", "Task", "Process", "Metric recovery", "Accepted", "Safe deploy", "Rounds", "Cost",
    ], tablefmt="github"))

    by_category = defaultdict(list)
    for t in trajectories:
        by_category[t.category or "uncategorized"].append(t)
    lines.extend(["", "## Per Category", ""])
    lines.append(tabulate([
        [category, len(items), f"{sum(t.success for t in items) / len(items):.1%}",
         f"{sum(1 for t in items if _process_score(t, event_map.get(t.alert_id, {}))['process_success']) / len(items):.1%}",
         f"{sum(1 for t in items if t.success and _process_score(t, event_map.get(t.alert_id, {}))['process_success']) / len(items):.1%}",
         f"{sum(_business_score(t, event_map.get(t.alert_id, {}))['metric_recovery'] for t in items) / len(items):.1%}",
         f"{sum(1 for t in items if _business_score(t, event_map.get(t.alert_id, {}))['accepted']) / len(items):.1%}",
         f"{sum(1 for t in items if _business_score(t, event_map.get(t.alert_id, {}))['stability_violation']) / len(items):.1%}",
         f"{sum(_fraud_score(t, event_map.get(t.alert_id, {}))['fraud_recall_recovery'] for t in items) / len(items):.1%}",
         f"{sum(1 for t in items if _fraud_score(t, event_map.get(t.alert_id, {}))['safe_deployment']) / len(items):.1%}",
         f"{sum(t.total_cost for t in items) / len(items):.2f}",
         ", ".join(sorted({t.expected_root_cause for t in items}))]
        for category, items in sorted(by_category.items())
    ], headers=[
        "Category", "N", "Task success", "Process success", "Overall",
        "Metric recovery", "Acceptance", "Stability violation", "Fraud recall", "Safe deploy",
        "Avg cost", "Root causes",
    ], tablefmt="github"))

    by_cause = defaultdict(list)
    for t in trajectories:
        by_cause[t.expected_root_cause].append(t)
    lines.extend(["", "## Per Root Cause", ""])
    lines.append(tabulate([
        [cause, len(items), f"{sum(t.success for t in items) / len(items):.1%}",
         f"{sum(t.total_cost for t in items) / len(items):.2f}"]
        for cause, items in sorted(by_cause.items())
    ], headers=["Root cause", "N", "Joint success", "Avg cost"], tablefmt="github"))
    return "\n".join(lines) + "\n"


def _business_score(traj, event: dict) -> dict:
    """Estimate production-style refresh outcome from the agent trajectory.

    This scorer mirrors ACRM-style business evaluation: accepted repairs must recover
    signal while staying within stability, false-positive, and coverage guardrails.
    It is deterministic so synthetic eval cases remain reproducible.
    """
    expected_gain = float(event.get("expected_gain", 0.08))
    if expected_gain <= 0:
        expected_gain = 0.0
    selected = traj.repair_strategy or "human_review"
    expected = traj.expected_repair
    handover = selected == "human_review"
    label_deferral = selected == "defer_until_label_mature"
    correct = selected == expected
    replay_metrics = _latest_replay_metrics(traj)

    # Prefer replay-observed values when the agent actually validated a repair.
    if replay_metrics:
        raw_gain = float(replay_metrics.get("metric_gain", 0.0))
        fp_rate = float(replay_metrics.get("fp_rate", 0.0))
        recall_gain = float(replay_metrics.get("amount_recall_gain", raw_gain * 0.9))
    elif correct and not handover:
        raw_gain = expected_gain
        fp_rate = float(event.get("targeted_fp_rate", 0.0015))
        recall_gain = expected_gain * 0.9
    elif label_deferral and expected == "defer_until_label_mature":
        raw_gain = 0.0
        fp_rate = 0.0
        recall_gain = 0.0
    elif handover:
        raw_gain = 0.0
        fp_rate = 0.0
        recall_gain = 0.0
    else:
        raw_gain = float(event.get("generic_gain", 0.005))
        fp_rate = float(event.get("generic_fp_rate", 0.006))
        recall_gain = raw_gain * 0.5

    psi_delta = _estimate_psi_delta(selected, correct, event)
    coverage_loss = _estimate_coverage_loss(selected, correct, event)
    review_workload_change = _estimate_review_workload_change(selected, correct, handover)
    stability_violation = (
        psi_delta > float(event.get("max_psi_delta", 0.10))
        or fp_rate > float(event.get("max_fp_rate", 0.005))
        or coverage_loss > float(event.get("max_coverage_loss", 0.03))
    )
    if expected == "defer_until_label_mature":
        accepted = label_deferral and not stability_violation
    else:
        accepted = correct and not handover and not stability_violation

    denom = max(abs(float(event.get("metric_drop", {}).get("recall_at_fpr", -expected_gain))), expected_gain, 1e-6)
    metric_recovery = max(0.0, min(raw_gain / denom, 1.0))
    recall_recovery = max(0.0, min(recall_gain / denom, 1.0))
    return {
        "metric_recovery": metric_recovery,
        "recall_recovery": recall_recovery,
        "stability_violation": stability_violation,
        "coverage_loss": coverage_loss,
        "false_positive_impact": fp_rate,
        "review_workload_change": review_workload_change,
        "accepted": accepted,
        "handover": handover,
    }


def _fraud_score(traj, event: dict) -> dict:
    business = _business_score(traj, event)
    replay_metrics = _latest_replay_metrics(traj)
    recall_drop = abs(float(event.get("metric_drop", {}).get("recall_at_fpr", -event.get("expected_gain", 0.08))))
    amount_drop = abs(float(event.get("metric_drop", {}).get("amount_recall", -event.get("expected_gain", 0.08))))
    denom_recall = max(recall_drop, float(event.get("expected_gain", 0.08)), 1e-6)
    denom_amount = max(amount_drop, float(event.get("expected_gain", 0.08)), 1e-6)

    if replay_metrics:
        fraud_recall_gain = float(replay_metrics.get("metric_gain", 0.0))
        amount_recall_gain = float(replay_metrics.get("amount_recall_gain", fraud_recall_gain * 0.9))
    elif traj.repair_strategy == traj.expected_repair and traj.repair_strategy not in {"human_review", "defer_until_label_mature"}:
        fraud_recall_gain = float(event.get("expected_gain", 0.08))
        amount_recall_gain = fraud_recall_gain * 0.9
    else:
        fraud_recall_gain = 0.0
        amount_recall_gain = 0.0

    fraud_recall_recovery = max(0.0, min(fraud_recall_gain / denom_recall, 1.0))
    amount_recall_recovery = max(0.0, min(amount_recall_gain / denom_amount, 1.0))
    segment_impact = max([abs(float(v)) for v in event.get("affected_segments", {}).values()] or [0.0])
    segment_recovery = fraud_recall_recovery if segment_impact >= 0.10 else business["metric_recovery"]

    is_novel_attack_case = (
        event.get("category") == "C_AdversarialDrift"
        or event.get("root_cause") == "attack_pattern_drift"
    )
    novel_attack_detected = (
        traj.diagnosed_root_cause == "attack_pattern_drift"
        or traj.repair_strategy == "rule_update"
    )
    is_label_maturity_case = event.get("root_cause") == "label_delay"
    label_maturity_guard_ok = (
        not is_label_maturity_case
        or traj.repair_strategy in {"defer_until_label_mature", "human_review"}
    )
    is_rule_update_case = event.get("expected_repair") == "rule_update"
    replay_passed = bool(replay_metrics.get("passed")) if replay_metrics else False
    if not is_rule_update_case:
        rule_robustness = 1.0
    elif traj.repair_strategy != "rule_update":
        rule_robustness = 0.0
    elif replay_passed:
        rule_robustness = 1.0
    else:
        # A rule update without replay is useful but not production-robust.
        rule_robustness = 0.5

    process = _process_score(traj, event)
    safe_deployment = (
        business["accepted"]
        and process["process_success"]
        and not business["stability_violation"]
        and business["false_positive_impact"] <= float(event.get("max_fp_rate", 0.005))
    )
    time_to_mitigation_hours = _estimate_time_to_mitigation_hours(traj, event, safe_deployment)
    return {
        "fraud_recall_recovery": fraud_recall_recovery,
        "amount_recall_recovery": amount_recall_recovery,
        "segment_recovery": segment_recovery,
        "is_novel_attack_case": is_novel_attack_case,
        "novel_attack_detected": novel_attack_detected,
        "is_label_maturity_case": is_label_maturity_case,
        "label_maturity_guard_ok": label_maturity_guard_ok,
        "is_rule_update_case": is_rule_update_case,
        "rule_robustness": rule_robustness,
        "safe_deployment": safe_deployment,
        "time_to_mitigation_hours": time_to_mitigation_hours,
    }


def _estimate_time_to_mitigation_hours(traj, event: dict, safe_deployment: bool) -> float:
    if traj.repair_strategy == "human_review":
        return float(event.get("manual_handover_hours", 24.0))
    base = 0.35 * len(traj.steps) + 0.25 * float(traj.total_cost)
    if traj.repair_strategy == "full_retraining":
        base += 8.0
    elif traj.repair_strategy == "partial_retraining":
        base += 4.0
    elif traj.repair_strategy == "defer_until_label_mature":
        base += 12.0
    elif traj.repair_strategy in {"rule_update", "feature_patch", "threshold_adjustment"}:
        base += 1.5
    if not safe_deployment:
        base += 6.0
    return round(base, 2)


def _to_namespace(obj):
    if isinstance(obj, dict):
        return AttrDict(**{k: _to_namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_namespace(v) for v in obj]
    return obj


def _latest_replay_metrics(traj) -> dict:
    for step in reversed(traj.steps):
        if step.action.action_type == "run_replay_backtest":
            return step.outcome.metrics or {}
    return {}


def _estimate_psi_delta(strategy: str, correct: bool, event: dict) -> float:
    if strategy in {"human_review", "defer_until_label_mature"}:
        return 0.0
    if correct:
        return {
            "feature_patch": 0.015,
            "threshold_adjustment": 0.025,
            "rule_update": 0.030,
            "partial_retraining": 0.040,
            "full_retraining": 0.060,
        }.get(strategy, 0.04)
    return {
        "feature_patch": 0.090,
        "threshold_adjustment": 0.070,
        "rule_update": 0.080,
        "partial_retraining": 0.120,
        "full_retraining": 0.160,
    }.get(strategy, 0.08)


def _estimate_coverage_loss(strategy: str, correct: bool, event: dict) -> float:
    if strategy in {"human_review", "defer_until_label_mature"}:
        return 0.0
    if correct:
        return {
            "feature_patch": 0.004,
            "threshold_adjustment": 0.010,
            "rule_update": 0.015,
            "partial_retraining": 0.008,
            "full_retraining": 0.020,
        }.get(strategy, 0.01)
    return {
        "feature_patch": 0.025,
        "threshold_adjustment": 0.030,
        "rule_update": 0.045,
        "partial_retraining": 0.035,
        "full_retraining": 0.060,
    }.get(strategy, 0.035)


def _estimate_review_workload_change(strategy: str, correct: bool, handover: bool) -> float:
    if handover:
        return 0.18
    if strategy == "defer_until_label_mature":
        return 0.05
    if correct:
        return {
            "feature_patch": -0.08,
            "threshold_adjustment": -0.04,
            "rule_update": -0.10,
            "partial_retraining": -0.07,
            "full_retraining": -0.03,
        }.get(strategy, -0.04)
    return 0.08


def _process_score(traj, event: dict) -> dict:
    actions = [step.action.action_type for step in traj.steps]
    required = event.get("required_actions", [])
    forbidden = event.get("forbidden_actions", [])
    required_hits = sum(1 for action in required if action in actions)
    required_recall = required_hits / len(required) if required else 1.0
    forbidden_called = any(action in actions for action in forbidden)
    max_cost = event.get("max_tool_cost")
    cost_ok = max_cost is None or traj.total_cost <= float(max_cost)
    process_success = required_recall == 1.0 and not forbidden_called and cost_ok
    return {
        "required_recall": required_recall,
        "forbidden_called": forbidden_called,
        "cost_ok": cost_ok,
        "process_success": process_success,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="+", default=["baseline"],
                        choices=["baseline", "retrieval", "dpo", "dpo_retrieval", "full"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--category", type=str)
    parser.add_argument("--output-prefix", default="diagnosis_eval")
    parser.add_argument("--max-rounds", type=int, default=10)
    parser.add_argument("--from-memory", action="store_true",
                        help="Re-format existing logs/diagnosis_eval_memory_<mode>.jsonl without rerunning the agent.")
    args = parser.parse_args()

    tag = os.environ.get("LLM_MODEL", "mock").replace("/", "-").replace(":", "-")
    for mode in args.modes:
        if args.from_memory:
            _, report = load_from_memory(mode, args.category, args.limit)
        else:
            _, report = run(mode, args.limit, args.category, args.max_rounds)
        suffix = f"_{args.category}" if args.category else ""
        path = LOGS_DIR / f"{args.output_prefix}_{tag}_{mode}{suffix}.md"
        path.write_text(report)
        print(report)
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
