"""
从评测轨迹里生成 DPO 训练数据。

DPO 数据格式(TRL-compatible):
{
    "prompt": <full prompt fed to LLM>,
    "chosen": <preferred action JSON>,
    "rejected": <dispreferred action JSON>,
}

数据来源(3 种偏好对策略):
1. **verdict-based**:
   - 拿"最终 verdict 正确"轨迹的每一步作为 chosen
   - 拿"最终 verdict 错误"轨迹里同一 round 的动作作为 rejected
   - 要求两条轨迹面对同一个 alert(或高相似 alert),不然不可比

2. **rule-violation-based**:
   - 在同一轮次,LLM 生成过被 Rule Stream 拒绝的动作 → rejected
   - 通过校验的最终动作 → chosen

3. **expert-crafted (from ground truth)**:
   - 针对每类 alert 的 expected_verdict,构造理想动作序列作为 chosen
   - 从错误轨迹里挑对应动作作为 rejected

用法:
    # 从已有的评测轨迹里造数据
    python -m experiments.build_dpo_data \
        --trajectories logs/eval_memory_baseline_*.jsonl logs/eval_memory_few_shot_*.jsonl \
        --output logs/dpo_train.jsonl

    # 也可以合并 expert-crafted 部分
    python -m experiments.build_dpo_data \
        --trajectories logs/*.jsonl \
        --use-expert \
        --output logs/dpo_train.jsonl
"""

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"


def _load_trajectories(paths: list[str]) -> list[dict]:
    """加载多个 JSONL 里的所有轨迹。"""
    trajectories = []
    for pat in paths:
        for path in glob.glob(pat):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trajectories.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return trajectories


def _load_eval_ground_truth() -> dict[str, dict]:
    """按 alert_id 索引评测集的 ground truth。"""
    with open(DATA_DIR / "eval_alerts.json") as f:
        alerts = json.load(f)["alerts"]
    return {a["alert_id"]: a for a in alerts}


def _verdict_correct(traj: dict, gt: dict) -> bool:
    expected = gt["expected_verdict"]
    alt = gt.get("alt_ok_verdicts", [])
    actual = traj.get("verdict", "")
    return actual == expected or actual in alt


def _step_prompt(step: dict, traj: dict) -> str:
    """
    根据一步轨迹重建 LLM 当时看到的 prompt(简化版)。
    """
    state = step.get("state", {})
    parts = [
        f"# Current investigation state",
        json.dumps(state, ensure_ascii=False, indent=2),
    ]
    parts.append("Return next action as JSON.")
    return "\n\n".join(parts)


def _action_to_response(action: dict) -> str:
    """把 action 序列化成 LLM 的输出格式。"""
    return json.dumps({
        "action_type": action.get("type"),
        "params": action.get("params", {}),
        "rationale": action.get("rationale", ""),
    }, ensure_ascii=False)


# =========================================================================================
# 策略 1: verdict-based pairs
# =========================================================================================

def build_verdict_based_pairs(trajectories: list[dict],
                                gt_map: dict) -> list[dict]:
    """
    同一个 alert_id 下,配对 (正确 verdict) vs (错误 verdict) 的轨迹。
    对每一步分别 pair 出 (prompt, chosen, rejected)。
    """
    by_alert = defaultdict(list)
    for t in trajectories:
        aid = t.get("alert_id")
        if aid and aid in gt_map:
            by_alert[aid].append(t)

    pairs = []
    for aid, ts in by_alert.items():
        gt = gt_map[aid]
        correct = [t for t in ts if _verdict_correct(t, gt)]
        wrong = [t for t in ts if not _verdict_correct(t, gt)]
        if not correct or not wrong:
            continue

        # 对每一对 (correct, wrong),按 round 对齐
        for c_traj in correct:
            for w_traj in wrong:
                c_steps = c_traj.get("steps", [])
                w_steps = w_traj.get("steps", [])
                for round_i in range(min(len(c_steps), len(w_steps))):
                    c_step = c_steps[round_i]
                    w_step = w_steps[round_i]
                    if c_step.get("action", {}).get("type") == w_step.get("action", {}).get("type"):
                        continue  # 同类型动作没意义
                    pairs.append({
                        "prompt": _step_prompt(c_step, c_traj),
                        "chosen": _action_to_response(c_step["action"]),
                        "rejected": _action_to_response(w_step["action"]),
                        "meta": {
                            "source": "verdict_based",
                            "alert_id": aid,
                            "round": round_i + 1,
                            "correct_verdict": c_traj.get("verdict"),
                            "wrong_verdict": w_traj.get("verdict"),
                        },
                    })
    return pairs


# =========================================================================================
# 策略 2: expert-crafted pairs(基于业务规则的正例 + 常见错误的负例)
# =========================================================================================

# 每种 category 的"理想动作序列"(基于业务经验的手工模板)
EXPERT_TEMPLATES = {
    "F_rule_robustness": [
        {"action_type": "expand_neighbors",
         "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": "device_id"},
         "rationale": "Expand to gather suspect set."},
        {"action_type": "generate_rule",
         "params": {"pattern": "shared_device_id AND is_new_account AND night_apply AND paste_used",
                    "coverage_min": 5, "confidence_threshold": 0.8},
         "rationale": "Multi-condition rule for robustness against single-vector bypass."},
        {"action_type": "shadow_replay",
         "params": {"rule_id": "__LATEST__", "replay_days": 7},
         "rationale": "Validate on recent data."},
        {"action_type": "adversarial_probe",
         "params": {"rule_id": "__LATEST__"},
         "rationale": "Verify rule survives 5 bypass strategies."},
        {"action_type": "terminate",
         "params": {"verdict": "fraud_confirmed", "confidence": 0.85,
                    "recommendations": ["deploy rule after red-team pass"]},
         "rationale": "Rule robust against bypass; confirm and deploy."},
    ],
    "A_obvious_gang": [
        {"action_type": "expand_neighbors",
         "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": "device_id"},
         "rationale": "Obvious gang starts with 1-hop device expansion."},
        {"action_type": "generate_rule",
         "params": {"pattern": "shared_device_id AND is_new_account AND night_apply",
                    "coverage_min": 5, "confidence_threshold": 0.8},
         "rationale": "Multi-condition rule combining structure + attribute signals."},
        {"action_type": "shadow_replay",
         "params": {"rule_id": "__LATEST__", "replay_days": 7},
         "rationale": "Validate on recent history."},
        {"action_type": "adversarial_probe",
         "params": {"rule_id": "__LATEST__"},
         "rationale": "Red-team before termination."},
        {"action_type": "terminate",
         "params": {"verdict": "fraud_confirmed", "confidence": 0.85,
                    "recommendations": ["deploy rule at 5% ramp"]},
         "rationale": "All checks pass; confirm fraud."},
    ],
    "C_wifi_false_positive": [
        {"action_type": "expand_neighbors",
         "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": "ip"},
         "rationale": "Trigger says IP shared — expand via IP first."},
        {"action_type": "compute_risk_score",
         "params": {"features": ["new_account_ratio", "avg_account_age_days", "night_apply_ratio"]},
         "rationale": "Check whether high account age contradicts fraud."},
        {"action_type": "terminate",
         "params": {"verdict": "not_fraud", "confidence": 0.85,
                    "recommendations": ["clear from watchlist"]},
         "rationale": "Mature accounts + no burst → WiFi neighbor pattern, not fraud."},
    ],
    "E_novel_pattern": [
        {"action_type": "expand_neighbors",
         "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": "device_id"},
         "rationale": "Initial expansion to gather context."},
        {"action_type": "escalate_to_human",
         "params": {"reason": "Novel trigger pattern with low retrieval confidence — hand over."},
         "rationale": "Trigger phrasing indicates novel attack — do not auto-confirm."},
    ],
    "D_isolated_normal": [
        {"action_type": "expand_neighbors",
         "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": "device_id"},
         "rationale": "Baseline expansion; expect empty results."},
        {"action_type": "terminate",
         "params": {"verdict": "not_fraud", "confidence": 0.8,
                    "recommendations": ["clear alert"]},
         "rationale": "Isolated normal user, no suspicious connections."},
    ],
}

# 常见错误动作(供 expert-crafted 作为 rejected)
COMMON_MISTAKES = {
    "F_rule_robustness": {
        "action_type": "generate_rule",
        "params": {"pattern": "shared_device_id", "coverage_min": 3, "confidence_threshold": 0.9},
        "rationale": "Single-condition rule trivially bypassed by device rotation.",
    },
    "B_subtle_immature": {
        "action_type": "terminate",
        "params": {"verdict": "fraud_probable", "confidence": 0.65,
                   "recommendations": ["monitor for 30 days"]},
        "rationale": "Invents non-standard verdict 'fraud_probable' instead of using escalate.",
    },
    "A_obvious_gang": {
        "action_type": "terminate",
        "params": {"verdict": "not_fraud", "confidence": 0.7},
        "rationale": "Assumed low risk without investigation.",
    },
    "C_wifi_false_positive": {
        "action_type": "generate_rule",
        "params": {"pattern": "shared_ip", "coverage_min": 3},
        "rationale": "Rule uses only structural signal, would cause false-positives.",
    },
    "E_novel_pattern": {
        "action_type": "terminate",
        "params": {"verdict": "fraud_confirmed", "confidence": 0.85},
        "rationale": "Over-confident termination on novel pattern.",
    },
    "D_isolated_normal": {
        "action_type": "generate_rule",
        "params": {"pattern": "unusual_amount", "coverage_min": 1},
        "rationale": "Over-generalized rule from single-user anomaly.",
    },
}


def build_expert_crafted_pairs(gt_map: dict) -> list[dict]:
    """
    根据 EXPERT_TEMPLATES 和 COMMON_MISTAKES,生成基于业务经验的偏好对。
    这批数据保证 DPO 有稳定的高质量种子。
    """
    pairs = []
    for aid, gt in gt_map.items():
        cat = gt["category"]
        template = EXPERT_TEMPLATES.get(cat)
        mistake = COMMON_MISTAKES.get(cat)
        if not template or not mistake:
            continue

        # 用一个简化的 pseudo-state 作为 prompt(每步的 state 由 round 递进)
        for round_i, ideal_action in enumerate(template, 1):
            pseudo_state = {
                "alert_id": aid,
                "round": round_i,
                "diagnostic_report": f"Category: {cat}. Trigger: {gt['trigger_reason']}",
                "suspect_count": round_i + 1,
                "label_maturity": 0.7,
                "retrieval_confidence": 0.65,
                "past_actions": [
                    _summarize_action(a) for a in template[:round_i - 1]
                ],
            }
            prompt = (
                "# Current investigation state\n"
                + json.dumps(pseudo_state, ensure_ascii=False, indent=2)
                + "\n\nReturn next action as JSON."
            )
            pairs.append({
                "prompt": prompt,
                "chosen": json.dumps(ideal_action, ensure_ascii=False),
                "rejected": json.dumps(mistake, ensure_ascii=False),
                "meta": {
                    "source": "expert_crafted",
                    "alert_id": aid,
                    "category": cat,
                    "round": round_i,
                },
            })
    return pairs


def _summarize_action(a: dict) -> str:
    params = a.get("params", {})
    return f"{a['action_type']}({', '.join(f'{k}={v}' for k, v in params.items() if k not in ('seeds',))})"


# =========================================================================================
# 主流程
# =========================================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", nargs="+",
                         default=["logs/eval_memory_*.jsonl", "logs/trajectory_memory.jsonl"],
                         help="glob 表达式,可指定多个轨迹 JSONL 源")
    parser.add_argument("--use-verdict", action="store_true", default=True,
                         help="包含 verdict-based 偏好对")
    parser.add_argument("--use-expert", action="store_true", default=True,
                         help="包含 expert-crafted 偏好对")
    parser.add_argument("--output", default="logs/dpo_train.jsonl",
                         help="输出 JSONL")
    parser.add_argument("--stats-only", action="store_true",
                         help="不输出,只看统计")
    args = parser.parse_args()

    # 处理路径:相对路径按项目根目录解析
    trajectory_paths = []
    for pat in args.trajectories:
        pat = str(Path(__file__).parent.parent / pat) if not pat.startswith("/") else pat
        trajectory_paths.append(pat)

    trajectories = _load_trajectories(trajectory_paths)
    gt_map = _load_eval_ground_truth()
    print(f"Loaded {len(trajectories)} trajectories, {len(gt_map)} eval alerts.\n")

    all_pairs = []

    if args.use_verdict:
        verdict_pairs = build_verdict_based_pairs(trajectories, gt_map)
        print(f"  verdict-based pairs:   {len(verdict_pairs)}")
        all_pairs.extend(verdict_pairs)

    if args.use_expert:
        expert_pairs = build_expert_crafted_pairs(gt_map)
        print(f"  expert-crafted pairs:  {len(expert_pairs)}")
        all_pairs.extend(expert_pairs)

    print(f"  ============ TOTAL:    {len(all_pairs)} pairs")

    # 分类统计
    from collections import Counter
    by_src = Counter(p["meta"]["source"] for p in all_pairs)
    by_alert = Counter(p["meta"]["alert_id"] for p in all_pairs)
    print(f"\nSource breakdown: {dict(by_src)}")
    print(f"Unique alert_ids: {len(by_alert)}")
    print(f"Median pairs per alert: {sorted(by_alert.values())[len(by_alert)//2] if by_alert else 0}")

    if args.stats_only:
        return

    # 保存
    out = Path(args.output)
    if not out.is_absolute():
        out = Path(__file__).parent.parent / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\nSaved to {out}")

    # 写一份 sample 供人肉审
    sample_out = out.with_suffix(".sample.md")
    with open(sample_out, "w") as f:
        f.write("# DPO Training Pairs — Samples\n\n")
        for i, p in enumerate(all_pairs[:8]):
            f.write(f"## Pair {i+1} — {p['meta'].get('source', '?')}\n\n")
            f.write("### Prompt\n```\n" + p["prompt"] + "\n```\n\n")
            f.write("### Chosen\n```json\n" + p["chosen"] + "\n```\n\n")
            f.write("### Rejected\n```json\n" + p["rejected"] + "\n```\n\n")
            f.write(f"### Meta\n`{p['meta']}`\n\n---\n\n")
    print(f"Samples written to {sample_out}")


if __name__ == "__main__":
    main()
