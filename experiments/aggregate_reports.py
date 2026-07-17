"""
把 evaluate.py 分类跑出来的多份小报告合并成一份完整评测报告。

用法:
  python -m experiments.aggregate_reports \
    --inputs logs/eval_gpt4omini_AB.md logs/eval_C.md logs/eval_D.md logs/eval_E.md logs/eval_F.md \
    --mock  logs/eval_mock.md \
    --output logs/eval_final.md
"""
import argparse
import re
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"


def _parse_category_rows(text: str) -> list[tuple]:
    """从报告里抽取 category 行:| A_obvious_gang | 8 | 88% | 88% | 4.6 | ... |"""
    rows = []
    pattern = re.compile(
        r"\| ([ABCDEF]_\w+)\s*\|\s*(\d+)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+(?:\.\d+)?)\s*\|\s*([^|]+)\|"
    )
    for m in pattern.finditer(text):
        rows.append(m.groups())
    return rows


def _parse_rules(text: str) -> dict:
    out = {}
    m = re.search(r"Number of rules generated\s*\|\s*(\d+)", text)
    if m:
        out["n"] = int(m.group(1))
    m = re.search(r"Avg recall on holdout\s*\|\s*([\d.]+)%", text)
    if m:
        out["recall"] = float(m.group(1)) / 100
    m = re.search(r"Avg FP-rate on holdout\s*\|\s*([\d.]+)%", text)
    if m:
        out["fp_rate"] = float(m.group(1)) / 100
    m = re.search(r"Avg precision\s*\|\s*([\d.]+)%", text)
    if m:
        out["precision"] = float(m.group(1)) / 100
    return out


def _aggregate(files: list[Path], label: str) -> str:
    all_rows: dict[str, tuple] = {}   # category -> row
    rule_agg = {"n": 0, "recall_sum": 0.0, "fp_sum": 0.0, "prec_sum": 0.0}
    wrong_cases = []

    for path in files:
        if not path.exists():
            continue
        text = path.read_text()
        for row in _parse_category_rows(text):
            cat = row[0].strip()
            all_rows[cat] = row
        r = _parse_rules(text)
        if r.get("n"):
            rule_agg["n"] += r["n"]
            rule_agg["recall_sum"] += r["recall"] * r["n"]
            rule_agg["fp_sum"] += r["fp_rate"] * r["n"]
            rule_agg["prec_sum"] += r["precision"] * r["n"]
        # 收集 wrong cases
        m = re.search(r"## Wrong cases.*?\n\n((?:\|.*\n)+)", text, re.DOTALL)
        if m:
            for line in m.group(1).strip().split("\n"):
                if line.startswith("| eval_") or line.startswith("|eval_"):
                    wrong_cases.append(line)

    # 计算总体
    total_n = sum(int(r[1]) for r in all_rows.values())
    strict_correct = sum(int(r[1]) * int(r[2].rstrip("%")) / 100 for r in all_rows.values())
    lenient_correct = sum(int(r[1]) * int(r[3].rstrip("%")) / 100 for r in all_rows.values())
    strict_acc = strict_correct / total_n if total_n else 0
    lenient_acc = lenient_correct / total_n if total_n else 0

    avg_rounds_weighted = (
        sum(int(r[1]) * float(r[4]) for r in all_rows.values()) / total_n
        if total_n else 0
    )

    lines = [f"# Aggregated evaluation — {label}", ""]
    lines.append(f"**Total alerts**: {total_n}")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Strict accuracy | {strict_acc:.1%} |")
    lines.append(f"| Lenient accuracy | {lenient_acc:.1%} |")
    lines.append(f"| Avg rounds (weighted) | {avg_rounds_weighted:.1f} |")

    if rule_agg["n"]:
        lines.append(f"| Rules generated | {rule_agg['n']} |")
        lines.append(f"| Avg rule recall | {rule_agg['recall_sum']/rule_agg['n']:.1%} |")
        lines.append(f"| Avg rule FP-rate | {rule_agg['fp_sum']/rule_agg['n']:.2%} |")
        lines.append(f"| Avg rule precision | {rule_agg['prec_sum']/rule_agg['n']:.1%} |")

    lines.append("")
    lines.append("## Per-category")
    lines.append("")
    lines.append("| Category | N | Strict | Lenient | Rounds | Verdicts |")
    lines.append("|---|---|---|---|---|---|")
    for cat in sorted(all_rows):
        r = all_rows[cat]
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5].strip()} |")
    lines.append("")

    if wrong_cases:
        lines.append(f"## Wrong cases ({len(wrong_cases)})")
        lines.append("")
        lines.append("| Alert | Category | Expected | Actual | Conf | Rounds |")
        lines.append("|---|---|---|---|---|---|")
        lines.extend(wrong_cases)
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", nargs="+", required=True)
    p.add_argument("--mock", default=None, help="mock LLM report (for comparison)")
    p.add_argument("--output", default="eval_final.md")
    args = p.parse_args()

    real = _aggregate([Path(f) for f in args.inputs], "GPT-4o-mini (Full AFAM)")
    reports = [real]
    if args.mock:
        mock = _aggregate([Path(args.mock)], "Mock LLM (Full AFAM)")
        reports.append(mock)

    out = "\n\n---\n\n".join(reports)
    out_path = LOGS_DIR / args.output
    with open(out_path, "w") as f:
        f.write(out)
    print(out)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
