"""
评测:在 34 条打标告警上跑 Agent,输出完整评测报告。

评测维度:
1. 总体准确率(strict / lenient)
2. 各类别的表现(A/B/C/D/E/F)
3. 置信度校准(高置信是否 = 高准确)
4. 轮数 / 时间分布
5. 规则质量(生成规则的召回率与误伤率)
6. 与消融配置的对比

用法:
    # Mock LLM(默认,快,免费)
    LLM_MODEL=mock python -m experiments.evaluate

    # Real LLM(准,慢)
    LLM_MODEL=gpt-4o-mini OPENAI_API_KEY=xxx python -m experiments.evaluate

    # 只跑某类别
    LLM_MODEL=mock python -m experiments.evaluate --category A_obvious_gang

    # 跑多配置对比(慢)
    LLM_MODEL=mock python -m experiments.evaluate --compare
"""

import argparse
import json
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tabulate import tabulate

from src.memory import TrajectoryMemory
from src.orchestrator import Orchestrator, OrchestratorConfig

DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"


@dataclass
class AlertResult:
    """单条告警的评测结果。"""
    alert_id: str
    category: str
    difficulty: str
    expected_verdict: str
    alt_ok_verdicts: list
    expected_conf_range: tuple
    actual_verdict: str
    actual_confidence: float
    rounds: int
    time_sec: float
    strict_correct: bool          # verdict 完全匹配
    lenient_correct: bool          # verdict 匹配或落在 alt_ok 里
    conf_calibrated: bool          # 置信度落在期望范围
    generated_rule: dict | None    # 若生成过规则,记录其效果
    trajectory: Any = None


def _classify(actual_verdict: str, actual_conf: float, alert: dict) -> tuple[bool, bool, bool]:
    exp = alert["expected_verdict"]
    alt = alert.get("alt_ok_verdicts", [])
    strict = actual_verdict == exp
    lenient = strict or actual_verdict in alt
    cmin, cmax = alert.get("expected_confidence_range", [0.0, 1.0])
    conf_ok = cmin <= actual_conf <= cmax
    return strict, lenient, conf_ok


def _extract_generated_rule(traj) -> dict | None:
    """从轨迹里找 shadow_replay 的评估结果,反映规则质量。"""
    for step in traj.steps:
        if step.action.action_type == "shadow_replay":
            m = step.outcome.metrics
            return {
                "rule_id": m.get("rule_id"),
                "recall": m.get("recall", 0.0),
                "fp_rate": m.get("fp_rate", 0.0),
                "precision": m.get("precision", 0.0),
                "hits": m.get("hits_total", 0),
            }
    return None


def run_evaluation(config: OrchestratorConfig,
                    alerts: list[dict],
                    label: str = "eval") -> list[AlertResult]:
    memory_path = LOGS_DIR / f"eval_memory_{label}.jsonl"
    if memory_path.exists():
        memory_path.unlink()
    # 固定本轮开始时的检索库：当前评测样本仍落盘，但不能被后续样本检索，
    # 防止顺序泄漏导致分数虚高且不可复现。
    memory = TrajectoryMemory(path=memory_path, index_writes=False)
    orch = Orchestrator(config=config, memory=memory)

    results = []
    for i, alert in enumerate(alerts, 1):
        t0 = time.time()
        traj = orch.investigate(alert)
        actual_verdict = traj.verdict or "escalate"
        actual_conf = traj.final_confidence
        strict, lenient, conf_ok = _classify(actual_verdict, actual_conf, alert)
        rule_metric = _extract_generated_rule(traj)
        results.append(AlertResult(
            alert_id=alert["alert_id"],
            category=alert["category"],
            difficulty=alert["difficulty"],
            expected_verdict=alert["expected_verdict"],
            alt_ok_verdicts=alert.get("alt_ok_verdicts", []),
            expected_conf_range=tuple(alert.get("expected_confidence_range", [0, 1])),
            actual_verdict=actual_verdict,
            actual_confidence=actual_conf,
            rounds=len(traj.steps),
            time_sec=time.time() - t0,
            strict_correct=strict,
            lenient_correct=lenient,
            conf_calibrated=conf_ok,
            generated_rule=rule_metric,
        ))
        mark = "✓" if lenient else "✗"
        print(f"  [{i}/{len(alerts)}] {alert['alert_id']} ({alert['category']}) "
              f"→ {actual_verdict} conf={actual_conf:.2f} rounds={len(traj.steps)} {mark}")
    return results


def summary_metrics(results: list[AlertResult]) -> dict:
    n = len(results)
    strict = sum(r.strict_correct for r in results) / n if n else 0
    lenient = sum(r.lenient_correct for r in results) / n if n else 0
    conf_ok = sum(r.conf_calibrated for r in results) / n if n else 0
    avg_rounds = sum(r.rounds for r in results) / n if n else 0
    avg_time = sum(r.time_sec for r in results) / n if n else 0
    return {
        "n": n,
        "strict_accuracy": strict,
        "lenient_accuracy": lenient,
        "confidence_calibrated_rate": conf_ok,
        "avg_rounds": avg_rounds,
        "avg_time_sec": avg_time,
    }


def per_category(results: list[AlertResult]) -> dict:
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    out = {}
    for cat, rs in by_cat.items():
        n = len(rs)
        out[cat] = {
            "n": n,
            "strict_acc": sum(r.strict_correct for r in rs) / n,
            "lenient_acc": sum(r.lenient_correct for r in rs) / n,
            "avg_rounds": sum(r.rounds for r in rs) / n,
            "verdicts": dict(Counter(r.actual_verdict for r in rs)),
        }
    return out


def confidence_calibration(results: list[AlertResult]) -> list[dict]:
    """按置信度分箱,看每箱的正确率。"""
    bins = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.0)]
    out = []
    for lo, hi in bins:
        # 只看做出 verdict(不含 escalate)的 case
        in_bin = [r for r in results
                   if lo <= r.actual_confidence < hi + (0.001 if hi == 1.0 else 0)
                   and r.actual_verdict != "escalate"]
        if not in_bin:
            out.append({"range": f"[{lo:.2f},{hi:.2f})", "n": 0, "acc": None})
        else:
            acc = sum(r.strict_correct for r in in_bin) / len(in_bin)
            out.append({"range": f"[{lo:.2f},{hi:.2f})", "n": len(in_bin), "acc": acc})
    return out


def rule_quality_summary(results: list[AlertResult]) -> dict:
    rules = [r.generated_rule for r in results if r.generated_rule]
    if not rules:
        return {"n_rules": 0}
    return {
        "n_rules": len(rules),
        "avg_recall": sum(r["recall"] for r in rules) / len(rules),
        "avg_fp_rate": sum(r["fp_rate"] for r in rules) / len(rules),
        "avg_precision": sum(r["precision"] for r in rules) / len(rules),
    }


def format_report(config_name: str,
                    results: list[AlertResult],
                    total_time: float) -> str:
    summary = summary_metrics(results)
    per_cat = per_category(results)
    calib = confidence_calibration(results)
    rules = rule_quality_summary(results)

    lines = [f"# Evaluation report — {config_name}", ""]
    lines.append(f"**Total alerts**: {summary['n']}")
    lines.append(f"**Total wall-clock**: {total_time:.1f}s "
                  f"(avg {summary['avg_time_sec']:.1f}s per alert)")
    lines.append("")

    lines.append("## Overall metrics")
    lines.append("")
    lines.append(tabulate([
        ["Strict accuracy (verdict exact match)", f"{summary['strict_accuracy']:.1%}"],
        ["Lenient accuracy (incl. alt_ok_verdicts)", f"{summary['lenient_accuracy']:.1%}"],
        ["Confidence calibrated (in expected range)", f"{summary['confidence_calibrated_rate']:.1%}"],
        ["Avg rounds", f"{summary['avg_rounds']:.1f}"],
    ], tablefmt="github", headers=["Metric", "Value"]))
    lines.append("")

    lines.append("## Per-category breakdown")
    lines.append("")
    rows = []
    for cat in sorted(per_cat):
        d = per_cat[cat]
        verdicts_str = ", ".join(f"{k}={v}" for k, v in d["verdicts"].items())
        rows.append([
            cat, d["n"],
            f"{d['strict_acc']:.0%}",
            f"{d['lenient_acc']:.0%}",
            f"{d['avg_rounds']:.1f}",
            verdicts_str,
        ])
    lines.append(tabulate(rows, tablefmt="github",
                            headers=["Category", "N", "Strict", "Lenient", "Rounds", "Verdicts"]))
    lines.append("")

    lines.append("## Confidence calibration")
    lines.append("(Only for cases where Agent produced a non-escalate verdict)")
    lines.append("")
    rows = []
    for c in calib:
        acc_str = f"{c['acc']:.0%}" if c["acc"] is not None else "—"
        rows.append([c["range"], c["n"], acc_str])
    lines.append(tabulate(rows, tablefmt="github",
                            headers=["Conf range", "N", "Strict acc"]))
    lines.append("")

    lines.append("## Generated rule quality")
    lines.append("")
    if rules["n_rules"] == 0:
        lines.append("No rules generated in this run.")
    else:
        lines.append(tabulate([
            ["Number of rules generated", rules["n_rules"]],
            ["Avg recall on holdout", f"{rules['avg_recall']:.1%}"],
            ["Avg FP-rate on holdout", f"{rules['avg_fp_rate']:.2%}"],
            ["Avg precision", f"{rules['avg_precision']:.1%}"],
        ], tablefmt="github", headers=["Metric", "Value"]))
    lines.append("")

    # 错例清单
    wrong = [r for r in results if not r.lenient_correct]
    if wrong:
        lines.append("## Wrong cases (need attention)")
        lines.append("")
        rows = []
        for r in wrong:
            rows.append([
                r.alert_id, r.category,
                r.expected_verdict, r.actual_verdict,
                f"{r.actual_confidence:.2f}", r.rounds,
            ])
        lines.append(tabulate(rows, tablefmt="github",
                                headers=["Alert", "Category", "Expected", "Actual",
                                        "Conf", "Rounds"]))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, help="filter to one category")
    parser.add_argument("--compare", action="store_true",
                         help="compare Full vs No-Retrieval vs Rule-Only (slower)")
    parser.add_argument("--limit", type=int, help="only run first N alerts (for quick test)")
    parser.add_argument("--output", type=str, default="eval_report.md",
                         help="output report file name (under logs/)")
    args = parser.parse_args()

    with open(DATA_DIR / "eval_alerts.json") as f:
        alerts = json.load(f)["alerts"]

    if args.category:
        alerts = [a for a in alerts if a["category"] == args.category]
        print(f"Filtered to category={args.category}: {len(alerts)} alerts")
    if args.limit:
        alerts = alerts[:args.limit]

    configs = {"Full AFAM": OrchestratorConfig(log_verbose=False)}
    if args.compare:
        configs["No-Retrieval"] = OrchestratorConfig(use_retrieval=False, log_verbose=False)
        configs["Rule-Only"] = OrchestratorConfig(use_retrieval=False, use_alignment=False, log_verbose=False)

    all_reports = []
    for name, cfg in configs.items():
        print(f"\n===== Running {name} on {len(alerts)} alerts =====\n")
        t0 = time.time()
        results = run_evaluation(cfg, alerts, label=name.replace(" ", "_"))
        elapsed = time.time() - t0
        report = format_report(name, results, elapsed)
        all_reports.append(report)
        print("\n" + report + "\n")

    # 保存
    out_path = LOGS_DIR / args.output
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n\n---\n\n".join(all_reports))
    print(f"\nFull report saved to {out_path}")


if __name__ == "__main__":
    main()
