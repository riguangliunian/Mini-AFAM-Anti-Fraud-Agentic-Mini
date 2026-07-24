"""
对比 baseline / few_shot / dpo / dpo_retrieval 等模式在同一模型下的效果。

三档 mode 含义:
- baseline:  无 case few-shot,无 alignment 偏好提示(仅硬护栏)
- few_shot:  有 case few-shot,无 alignment 偏好提示
- dpo:       偏好已训进权重(需要 DPO 后的 checkpoint),prompt 里不再叠加
- dpo_retrieval: DPO 权重 + Top-3 完整历史轨迹 + 硬规则(论文 Full ACRM)

用法:
    # 本地 Ollama + Qwen3-4B
    export OPENAI_BASE_URL=http://localhost:11434/v1
    export LLM_MODEL=qwen3:4b
    python -m experiments.compare_modes --modes baseline few_shot

    # DPO 后的模型(等训完再跑)
    export LLM_MODEL=qwen3-4b-dpo
    python -m experiments.compare_modes --modes dpo

    # 一次跑全 3 组(需要 DPO checkpoint 已就绪)
    python -m experiments.compare_modes --modes baseline few_shot dpo

输出:
- 每 mode 一份 eval_<mode>_<model_tag>.md
- 一份合并对比表 eval_compare_<model_tag>.md
"""

import argparse
import json
import os
import time
from pathlib import Path

from tabulate import tabulate

from experiments.evaluate import (
    run_evaluation, summary_metrics, per_category, rule_quality_summary
)
from src.orchestrator import OrchestratorConfig

DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"


MODE_DESCRIPTIONS = {
    "baseline": "无 case few-shot + 无 alignment 偏好(纯硬护栏 + 语义级动作空间)",
    "few_shot": "有 case few-shot + 无 alignment 偏好(检索历史成功轨迹作示范)",
    "dpo":      "DPO 训练后的模型(偏好在权重里,prompt 不再叠加软偏好)",
    "dpo_retrieval": "DPO 权重 + Top-3 完整历史轨迹 retrieval + 硬规则(论文式 Full ACRM)",
    "full":     "三流全开(retrieval + alignment + rules)",
}


def _model_tag() -> str:
    """由 LLM_MODEL + LLM_TEMPERATURE 生成一个文件名友好的 tag。"""
    m = os.environ.get("LLM_MODEL", "unknown")
    tag = m.replace(":", "-").replace("/", "-").replace(" ", "-")
    t = os.environ.get("LLM_TEMPERATURE")
    if t:
        tag += f"_t{t}"
    # 允许用户显式加运行 tag(如 run1/run2/run3)
    extra = os.environ.get("RUN_TAG")
    if extra:
        tag += f"_{extra}"
    return tag


def _load_alerts(category: str | None = None, limit: int | None = None) -> list[dict]:
    with open(DATA_DIR / "eval_alerts.json") as f:
        alerts = json.load(f)["alerts"]
    if category:
        alerts = [a for a in alerts if a["category"] == category]
    if limit:
        alerts = alerts[:limit]
    return alerts


def _short_summary(results, config_label: str) -> dict:
    summary = summary_metrics(results)
    rq = rule_quality_summary(results)
    return {
        "config": config_label,
        "n": summary["n"],
        "strict_acc": summary["strict_accuracy"],
        "lenient_acc": summary["lenient_accuracy"],
        "avg_rounds": summary["avg_rounds"],
        "avg_time_sec": summary["avg_time_sec"],
        "n_rules": rq.get("n_rules", 0),
        "rule_recall": rq.get("avg_recall", 0.0) if rq.get("n_rules") else 0.0,
        "rule_precision": rq.get("avg_precision", 0.0) if rq.get("n_rules") else 0.0,
        "rule_fp_rate": rq.get("avg_fp_rate", 0.0) if rq.get("n_rules") else 0.0,
    }


def _format_compare(summaries: list[dict], model_tag: str) -> str:
    lines = [f"# 对比评测报告 — base model: `{model_tag}`", ""]
    lines.append(f"评测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 主对比表
    rows = []
    for s in summaries:
        rows.append([
            s["config"],
            s["n"],
            f"{s['strict_acc']:.1%}",
            f"{s['lenient_acc']:.1%}",
            f"{s['avg_rounds']:.1f}",
            f"{s['avg_time_sec']:.1f}s",
            s["n_rules"],
            f"{s['rule_recall']:.1%}",
            f"{s['rule_precision']:.1%}",
            f"{s['rule_fp_rate']:.2%}",
        ])
    lines.append("## 汇总对比")
    lines.append("")
    lines.append(tabulate(
        rows,
        headers=["Mode", "N", "Strict Acc", "Lenient Acc", "Rounds",
                 "Avg Time", "#Rules", "Rule Recall", "Rule Precision", "Rule FP"],
        tablefmt="github",
    ))
    lines.append("")

    lines.append("## Mode 说明")
    lines.append("")
    for s in summaries:
        mode = s["config"].lower()
        desc = MODE_DESCRIPTIONS.get(mode, "-")
        lines.append(f"- **{s['config']}**: {desc}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="+",
                         default=["baseline", "few_shot"],
                         choices=["baseline", "few_shot", "dpo", "dpo_retrieval", "full"],
                         help="要跑的 mode 列表")
    parser.add_argument("--category", type=str, help="只跑某类告警")
    parser.add_argument("--limit", type=int, help="只跑前 N 条")
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--output-prefix", default="compare",
                         help="报告文件前缀")
    args = parser.parse_args()

    model_tag = _model_tag()
    print(f"\n============================================")
    print(f"  Base model: {os.environ.get('LLM_MODEL', 'mock')}")
    print(f"  Base URL:   {os.environ.get('OPENAI_BASE_URL', '(default)')}")
    print(f"  Modes:      {args.modes}")
    print(f"============================================\n")

    alerts = _load_alerts(args.category, args.limit)
    print(f"Loaded {len(alerts)} alerts for evaluation.\n")

    summaries = []
    for mode in args.modes:
        print(f"\n===== Mode: {mode} =====")
        print(f"  {MODE_DESCRIPTIONS.get(mode, '')}\n")

        config = OrchestratorConfig(
            mode=mode,
            max_rounds=args.max_rounds,
            log_verbose=False,
        )
        t0 = time.time()
        results = run_evaluation(config, alerts, label=f"{mode}_{model_tag}")
        elapsed = time.time() - t0

        # 每 mode 出一份详细报告
        from experiments.evaluate import format_report
        report = format_report(f"{mode} ({model_tag})", results, elapsed)
        detail_path = LOGS_DIR / f"{args.output_prefix}_{model_tag}_{mode}.md"
        with open(detail_path, "w") as f:
            f.write(report)
        print(f"  Detail saved: {detail_path}")

        summaries.append(_short_summary(results, mode))

    # 合并对比表
    compare_report = _format_compare(summaries, model_tag)
    compare_path = LOGS_DIR / f"{args.output_prefix}_{model_tag}_summary.md"
    with open(compare_path, "w") as f:
        f.write(compare_report)
    print(f"\n{compare_report}\n")
    print(f"Summary saved: {compare_path}")


if __name__ == "__main__":
    main()
