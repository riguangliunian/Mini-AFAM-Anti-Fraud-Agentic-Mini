"""构造论文 ACRM 附录 E 风格的完整轨迹 DPO 数据。

与旧版 ``build_dpo_data_acrm.py`` 的关键区别：
1. shared prompt 只包含场景和初始触发；
2. chosen/rejected 都是完整的多轮 STATE -> ACTION -> OUTCOME -> RESULT；
3. 只在同一 alert 内配对，确保初始问题严格可比；
4. Accepted-vs-Rejected 直接偏好，Accepted-vs-Accepted 用复合分数排序；
5. 按 alert 分组拆分 train/held-out，禁止同一 alert 泄漏到两边。

注意：本项目没有论文中的真实生产上线/审核标签和 Qwen-Embedding-8B，
因此使用同一 alert 作为 ``cos(s0_i, s0_j) > 0.75`` 的保守替代，并用
评测 ground truth 定义 accepted。这是可用数据上的最接近复现，不冒充原论文语料。
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from experiments.build_dpo_data_acrm import compute_composite_score


ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def _canonical_trajectory(traj: dict) -> dict:
    return {k: v for k, v in traj.items() if not k.startswith("_")}


def _trajectory_id(traj: dict) -> str:
    raw = json.dumps(_canonical_trajectory(traj), ensure_ascii=False,
                     sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_trajectories(patterns: list[str]) -> tuple[list[dict], int]:
    loaded: list[dict] = []
    for pattern in patterns:
        resolved = pattern if Path(pattern).is_absolute() else str(ROOT / pattern)
        for filename in sorted(glob.glob(resolved)):
            with open(filename, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    traj = json.loads(line)
                    if traj.get("alert_id") and traj.get("steps"):
                        loaded.append(traj)

    unique: dict[str, dict] = {}
    for traj in loaded:
        unique.setdefault(_trajectory_id(traj), traj)
    return list(unique.values()), len(loaded) - len(unique)


def load_ground_truth() -> dict[str, dict]:
    with open(DATA_DIR / "eval_alerts.json", encoding="utf-8") as f:
        alerts = json.load(f)["alerts"]
    return {a["alert_id"]: a for a in alerts}


def is_accepted(traj: dict, gt: dict) -> bool:
    """论文 accepted=通过审核并部署；这里只用严格期望结果近似。

    ``alt_ok_verdicts`` 代表评测时可宽容接受，不等价于一条值得学习的
    生产 accepted 轨迹，尤其不能把大量保守 escalate 当成 chosen。
    """
    return traj.get("verdict", "") == gt["expected_verdict"]


def shared_prompt(alert_id: str, gt: dict, traj: dict) -> str:
    """论文 E.4: shared prompt = SCENARIO + DRIFT_TRIGGER。"""
    return (
        f"[SCENARIO] {gt.get('category', alert_id)}\n"
        f"[DRIFT_TRIGGER] {traj.get('trigger_reason', gt.get('trigger_reason', ''))}\n"
    )


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def serialize_trajectory(traj: dict, accepted: bool) -> str:
    """论文 E.4 风格：保留每轮完整 state/action/outcome 和最终结果。"""
    lines: list[str] = []
    for round_i, step in enumerate(traj.get("steps", []), 1):
        state = step.get("state", {})
        action = step.get("action", {})
        outcome = step.get("outcome", {})
        lines.extend([
            f"[ROUND {round_i}]",
            f"<STATE> {_json_compact(state)}",
            f"<ACTION> {_json_compact({'action_type': action.get('type'), 'params': action.get('params', {}), 'rationale': action.get('rationale', '')})}",
            f"<OUTCOME> {_json_compact(outcome)}",
        ])
    result = {
        "status": "ACCEPTED" if accepted else "REJECTED",
        "verdict": traj.get("verdict", ""),
        "confidence": traj.get("final_confidence", 0.0),
        "rounds": len(traj.get("steps", [])),
    }
    lines.append(f"[RESULT] {_json_compact(result)}")
    return "\n".join(lines)


def make_pair(chosen: dict, rejected: dict, gt: dict,
              source: str, chosen_score: float, rejected_score: float) -> dict:
    chosen_accepted = is_accepted(chosen, gt)
    rejected_accepted = is_accepted(rejected, gt)
    return {
        "prompt": shared_prompt(chosen["alert_id"], gt, chosen),
        "chosen": serialize_trajectory(chosen, chosen_accepted),
        "rejected": serialize_trajectory(rejected, rejected_accepted),
        "meta": {
            "source": source,
            "alert_id": chosen["alert_id"],
            "initial_state_match": "same_alert",
            "initial_state_similarity": 1.0,
            "chosen_trajectory_id": _trajectory_id(chosen),
            "rejected_trajectory_id": _trajectory_id(rejected),
            "chosen_score": chosen_score,
            "rejected_score": rejected_score,
            "score_margin": round(chosen_score - rejected_score, 4),
            "chosen_rounds": len(chosen.get("steps", [])),
            "rejected_rounds": len(rejected.get("steps", [])),
        },
    }


def build_pairs_for_alert(trajs: list[dict], gt: dict,
                          max_ar: int, max_aa: int,
                          min_score_margin: float) -> list[dict]:
    scored = [(traj, compute_composite_score(traj, gt)) for traj in trajs]
    accepted = sorted((x for x in scored if is_accepted(x[0], gt)),
                      key=lambda x: x[1], reverse=True)
    rejected = sorted((x for x in scored if not is_accepted(x[0], gt)),
                      key=lambda x: x[1])
    pairs: list[dict] = []

    # 论文 E.2: Accepted vs Rejected，优先最好 accepted 对最差 rejected。
    ar_candidates = [(a, r) for a in accepted for r in rejected]
    ar_candidates.sort(key=lambda x: x[0][1] - x[1][1], reverse=True)
    for (chosen, c_score), (rejected_traj, r_score) in ar_candidates[:max_ar]:
        pairs.append(make_pair(chosen, rejected_traj, gt,
                               "accepted_vs_rejected", c_score, r_score))

    # 论文 E.2: Accepted vs Accepted，用最终可测结果的复合分数细排。
    aa_candidates = []
    for i, better in enumerate(accepted):
        for worse in accepted[i + 1:]:
            margin = better[1] - worse[1]
            if margin >= min_score_margin:
                aa_candidates.append((better, worse))
    aa_candidates.sort(key=lambda x: x[0][1] - x[1][1], reverse=True)
    for (chosen, c_score), (rejected_traj, r_score) in aa_candidates[:max_aa]:
        pairs.append(make_pair(chosen, rejected_traj, gt,
                               "accepted_vs_accepted", c_score, r_score))
    return pairs


def split_alerts(alert_ids: list[str], gt_map: dict[str, dict],
                 heldout_ratio: float, seed: int) -> tuple[set[str], set[str]]:
    """按 category 分层、按 alert 分组；无时间戳时替代论文 rolling split。"""
    by_category: dict[str, list[str]] = defaultdict(list)
    for alert_id in sorted(alert_ids):
        by_category[gt_map[alert_id].get("category", "unknown")].append(alert_id)
    rng = random.Random(seed)
    train: set[str] = set()
    heldout: set[str] = set()
    for ids in by_category.values():
        rng.shuffle(ids)
        if heldout_ratio <= 0 or len(ids) < 2:
            train.update(ids)
            continue
        n_heldout = max(1, round(len(ids) * heldout_ratio))
        n_heldout = min(n_heldout, len(ids) - 1)
        heldout.update(ids[:n_heldout])
        train.update(ids[n_heldout:])
    return train, heldout


def write_jsonl(path: Path, pairs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")


def dataset_stats(name: str, pairs: list[dict]) -> list[str]:
    sources = Counter(p["meta"]["source"] for p in pairs)
    chosen_lengths = [len(p["chosen"]) for p in pairs]
    rounds = [p["meta"]["chosen_rounds"] for p in pairs]
    verdicts = Counter()
    failed_outcome_pairs = 0
    for pair in pairs:
        result = json.loads(pair["chosen"].rsplit("[RESULT] ", 1)[1])
        verdicts[result["verdict"]] += 1
        if '"success":false' in pair["chosen"]:
            failed_outcome_pairs += 1
    lines = [f"## {name}", "", f"- Pairs: {len(pairs)}",
             f"- Alerts: {len({p['meta']['alert_id'] for p in pairs})}"]
    if pairs:
        lines.extend([
            f"- Accepted vs Rejected: {sources['accepted_vs_rejected']}",
            f"- Accepted vs Accepted: {sources['accepted_vs_accepted']}",
            f"- Avg chosen rounds: {statistics.mean(rounds):.2f}",
            f"- Avg chosen characters: {statistics.mean(chosen_lengths):.0f}",
            f"- Chosen verdicts: {dict(verdicts)}",
            f"- Chosen pairs containing failed intermediate outcomes: {failed_outcome_pairs}",
        ])
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", nargs="+",
                        default=["logs/eval_memory_*.jsonl"])
    parser.add_argument("--output", default="logs/dpo_full_trajectory_train.jsonl")
    parser.add_argument("--heldout-output",
                        default="logs/dpo_full_trajectory_heldout.jsonl")
    parser.add_argument("--heldout-ratio", type=float, default=0.2)
    parser.add_argument("--max-ar-per-alert", type=int, default=5)
    parser.add_argument("--max-aa-per-alert", type=int, default=3)
    parser.add_argument("--min-score-margin", type=float, default=0.08)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    trajectories, duplicate_count = load_trajectories(args.trajectories)
    gt_map = load_ground_truth()
    by_alert: dict[str, list[dict]] = defaultdict(list)
    for traj in trajectories:
        if traj.get("alert_id") in gt_map:
            by_alert[traj["alert_id"]].append(traj)

    pairs_by_alert: dict[str, list[dict]] = {}
    for alert_id, trajs in by_alert.items():
        pairs = build_pairs_for_alert(
            trajs, gt_map[alert_id], args.max_ar_per_alert,
            args.max_aa_per_alert, args.min_score_margin,
        )
        if pairs:
            pairs_by_alert[alert_id] = pairs

    train_alerts, heldout_alerts = split_alerts(
        list(pairs_by_alert), gt_map, args.heldout_ratio, args.seed)
    train_pairs = [p for aid in sorted(train_alerts) for p in pairs_by_alert[aid]]
    heldout_pairs = [p for aid in sorted(heldout_alerts) for p in pairs_by_alert[aid]]

    out = Path(args.output) if Path(args.output).is_absolute() else ROOT / args.output
    heldout_out = (Path(args.heldout_output) if Path(args.heldout_output).is_absolute()
                   else ROOT / args.heldout_output)
    write_jsonl(out, train_pairs)
    write_jsonl(heldout_out, heldout_pairs)

    overlap = train_alerts & heldout_alerts
    report = [
        "# Full-trajectory DPO dataset statistics",
        "",
        "论文对应: Appendix E.1-E.5。",
        "",
        f"- Loaded unique trajectories: {len(trajectories)}",
        f"- Removed exact duplicates: {duplicate_count}",
        f"- Alerts with usable pairs: {len(pairs_by_alert)}",
        f"- Train/held-out alert overlap: {len(overlap)}",
        "- Matching policy: same alert (conservative substitute for embedding cosine > 0.75)",
        "- Limitation: accepted/rejected comes from eval ground truth, not production deployment review",
        "- Paper scale: 3,012 train / 800 held-out pairs; this local corpus cannot reproduce that scale",
        "- Offline composite scores are retained only in meta and never exposed to either completion",
        "",
    ]
    report.extend(dataset_stats("Train", train_pairs))
    report.extend(dataset_stats("Held-out", heldout_pairs))
    report_path = out.with_suffix(".stats.md")
    report_path.write_text("\n".join(report), encoding="utf-8")

    sample_path = out.with_suffix(".sample.md")
    samples = (train_pairs[:2] + heldout_pairs[:1])
    with open(sample_path, "w", encoding="utf-8") as f:
        f.write("# Full-trajectory DPO samples\n\n")
        for i, pair in enumerate(samples, 1):
            f.write(f"## Pair {i}\n\n")
            f.write(f"Meta: `{pair['meta']}`\n\n")
            f.write("### Prompt\n```text\n" + pair["prompt"] + "```\n\n")
            f.write("### Chosen\n```text\n" + pair["chosen"] + "\n```\n\n")
            f.write("### Rejected\n```text\n" + pair["rejected"] + "\n```\n\n")

    print(f"Unique trajectories: {len(trajectories)} (duplicates removed: {duplicate_count})")
    print(f"Train pairs: {len(train_pairs)} -> {out}")
    print(f"Held-out pairs: {len(heldout_pairs)} -> {heldout_out}")
    print(f"Stats: {report_path}")
    print(f"Samples: {sample_path}")
    if overlap:
        raise RuntimeError(f"Alert leakage detected: {sorted(overlap)}")


if __name__ == "__main__":
    main()
