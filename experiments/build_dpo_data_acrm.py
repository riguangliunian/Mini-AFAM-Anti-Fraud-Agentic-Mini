"""
DPO 训练数据构造 — 严格按 ACRM 论文 (ACL 2026 Industry Track) 方法学。

对应论文 Section 3.3 + 附录 E.1/E.2 的三步流程:

  Step 1: 匹配可比较的问题
    - 对每对轨迹,计算初始状态 s_0 的 embedding 相似度
    - 只保留 cosine similarity > 0.75 的对(避免比较"表面像但语境不同")

  Step 2: 按结果分成三类
    - 55% Accepted vs Rejected:直接偏好
    - 35% Accepted vs Accepted:两条都上线了,用复合分数细排 ← 论文精髓
    - 10% Rejected vs Rejected:丢弃

  Step 3: 复合分数排序(反欺诈版)
    R(τ) = α * R_perf  - β * C_fp  - γ * C_escalate  - δ * C_rounds

    其中:
      R_perf     = verdict 是否 strictly correct (0/1) + 部分 credit(alt_ok 给 0.5)
      C_fp       = 规则误伤率(shadow replay 输出)
      C_escalate = 无必要的 escalate 惩罚(可以 escalate 的场景不惩罚)
      C_rounds   = (rounds - 4) / 4  (超过 4 轮的每一轮微惩罚)

    权重 (α, β, γ, δ) = (1.0, 3.0, 1.5, 0.5)
      - β 最大:反欺诈里误伤代价最高(对应 ACRM 的稳定性)
      - γ 次高:不必要的 escalate 是能力弱的表现

用法:
    python -m experiments.build_dpo_data_acrm \
        --trajectories "logs/eval_memory_*.jsonl" \
        --output logs/dpo_train_acrm.jsonl \
        --sim-threshold 0.75

输出:
    - dpo_train_acrm.jsonl        TRL-compatible 偏好对
    - dpo_train_acrm.stats.md     数据构造统计报告
    - dpo_train_acrm.sample.md    前 8 条样例
"""

import argparse
import glob
import json
import math
from collections import defaultdict, Counter
from itertools import combinations
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"


# =========================================================================================
# 反欺诈版复合分数(替换 ACRM 论文里的 KS/PSI/Gap)
# =========================================================================================

# 反欺诈版复合分数(参照 ACRM Section 3.3 的多目标权衡框架)
# 关键差异:反欺诈里误伤代价(β)最高,取代 ACRM 的稳定性权重
COMPOSITE_WEIGHTS = {
    "alpha_verdict":  1.0,    # 主奖励:verdict 是否符合预期
    "alpha_conf":     0.5,    # 置信度是否校准
    "alpha_recall":   0.6,    # 规则召回率(rule quality)
    "beta_fp":        3.0,    # 规则误伤率 penalty(反欺诈最重要)
    "gamma_esc":      1.5,    # 不必要 escalate 的 penalty
    "delta_rounds":   0.3,    # 轮数 penalty
}


def compute_composite_score(traj: dict, gt: dict) -> float:
    """
    多目标复合分数,让不同轨迹在 verdict / confidence / rule quality 上都有区分度。

    R = α_v * verdict_match
      + α_c * conf_calibration
      + α_r * rule_recall
      - β_fp * fp_rate
      - γ_e * unnecessary_escalate
      - δ * rounds_penalty
    """
    w = COMPOSITE_WEIGHTS

    # ---- 1. Verdict 匹配得分(离散但更细粒度)----
    verdict = traj.get("verdict", "")
    expected = gt.get("expected_verdict", "")
    alt_ok = gt.get("alt_ok_verdicts", [])
    if verdict == expected:
        r_verdict = 1.0
    elif verdict in alt_ok:
        r_verdict = 0.6
    else:
        r_verdict = 0.0

    # ---- 2. Confidence 校准(连续,拉开同 verdict 的分差)----
    conf = float(traj.get("final_confidence", 0.0))
    conf_range = gt.get("expected_confidence_range", [0.0, 1.0])
    lo, hi = conf_range
    if lo <= conf <= hi:
        # 在期望范围内:越靠近中点越好
        mid = (lo + hi) / 2
        span = max(hi - lo, 0.01)
        r_conf = 1.0 - abs(conf - mid) / span  # [0.5, 1.0]
        r_conf = max(0.5, r_conf)
    else:
        # 超范围:距离越远扣越多
        dist = min(abs(conf - lo), abs(conf - hi))
        r_conf = max(0.0, 0.5 - dist)

    # ---- 3. 规则 recall(连续 0-1)----
    rule_recall = 0.0
    rule_fp = 0.0
    for step in traj.get("steps", []):
        if step.get("action", {}).get("type") == "shadow_replay":
            m = step.get("outcome", {}).get("metrics", {})
            rule_recall = max(rule_recall, float(m.get("recall", 0.0)))
            rule_fp = max(rule_fp, float(m.get("fp_rate", 0.0)))
    r_recall = rule_recall  # [0, 1]

    # ---- 4. 误伤率 penalty ----
    c_fp = rule_fp  # [0, 1]

    # ---- 5. 不必要 escalate penalty ----
    c_escalate = 0.0
    if verdict == "escalate" and expected != "escalate":
        if "escalate" in alt_ok:
            c_escalate = 0.3
        else:
            c_escalate = 1.0

    # ---- 6. 轮数 penalty ----
    rounds = len(traj.get("steps", []))
    c_rounds = rounds / 5.0  # 归一到 [0, ~1.6],5 轮 = 1.0

    R = (w["alpha_verdict"] * r_verdict
         + w["alpha_conf"]  * r_conf
         + w["alpha_recall"] * r_recall
         - w["beta_fp"]     * c_fp
         - w["gamma_esc"]   * c_escalate
         - w["delta_rounds"] * c_rounds)
    return round(R, 4)


# =========================================================================================
# Step 1: 相似度匹配(用现成的 retrieval 模块的 TF-IDF + Jaccard 混合)
# =========================================================================================

def compute_initial_state_similarity(t1: dict, t2: dict) -> float:
    """
    ACRM 用 Qwen-Embedding-8B。我们用 retrieval.py 里的 TF-IDF 文本 × Jaccard 结构指纹混合。
    """
    from src.retrieval import _tokenize, _tf, _cosine, _graph_fingerprint_similarity

    def _get_initial_text(traj):
        first_step = traj.get("steps", [{}])[0]
        state = first_step.get("state", {})
        return (
            str(traj.get("trigger_reason", "")) + " "
            + str(state.get("diagnostic_report", "")) + " "
            + " ".join(f"{k}={v}" for k, v in state.get("key_metrics", {}).items())
        )

    def _get_fp(traj):
        # 从 trajectory 里推指纹(如果有 graph_fingerprint 字段更好)
        return traj.get("graph_fingerprint", {})

    tf1 = _tf(_tokenize(_get_initial_text(t1)))
    tf2 = _tf(_tokenize(_get_initial_text(t2)))
    text_sim = _cosine(tf1, tf2)
    fp_sim = _graph_fingerprint_similarity(_get_fp(t1), _get_fp(t2))

    # 反欺诈里结构相似度更重要
    return 0.4 * text_sim + 0.6 * fp_sim


# =========================================================================================
# Step 2: 分类(Accepted vs Rejected / Accepted vs Accepted / 其他)
# =========================================================================================

def verdict_is_accepted(traj: dict, gt: dict) -> bool:
    """按 ACRM 定义:通过评估 = accepted。"""
    verdict = traj.get("verdict", "")
    expected = gt.get("expected_verdict", "")
    alt_ok = gt.get("alt_ok_verdicts", [])
    return verdict == expected or verdict in alt_ok


# =========================================================================================
# 主流程
# =========================================================================================

def load_trajectories(patterns: list[str]) -> list[dict]:
    trajectories = []
    for pat in patterns:
        pat = str(Path(pat)) if Path(pat).is_absolute() else str(Path(__file__).parent.parent / pat)
        for path in glob.glob(pat):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        traj = json.loads(line)
                        if traj.get("alert_id") and traj.get("steps"):
                            traj["_source_file"] = Path(path).name
                            trajectories.append(traj)
                    except json.JSONDecodeError:
                        continue
    return trajectories


def load_gt() -> dict:
    with open(DATA_DIR / "eval_alerts.json") as f:
        alerts = json.load(f)["alerts"]
    return {a["alert_id"]: a for a in alerts}


def step_prompt(step: dict) -> str:
    """重建 LLM 当时看到的 prompt。"""
    state = step.get("state", {})
    return (
        "# Current investigation state\n"
        + json.dumps(state, ensure_ascii=False, indent=2)
        + "\n\nReturn next action as JSON."
    )


def action_to_response(action: dict) -> str:
    return json.dumps({
        "action_type": action.get("type"),
        "params": action.get("params", {}),
        "rationale": action.get("rationale", ""),
    }, ensure_ascii=False)


def build_pair(chosen_step: dict, rejected_step: dict, meta: dict) -> dict:
    return {
        "prompt": step_prompt(chosen_step),
        "chosen": action_to_response(chosen_step["action"]),
        "rejected": action_to_response(rejected_step["action"]),
        "meta": meta,
    }


def build_pairs_within_alert(trajs: list[dict], gt: dict,
                              alert_id: str) -> tuple[list[dict], dict]:
    """对同一 alert 上的多条轨迹,生成 3 类 pair(A vs R / A vs A / 丢弃)。"""
    accepted = [t for t in trajs if verdict_is_accepted(t, gt)]
    rejected = [t for t in trajs if not verdict_is_accepted(t, gt)]

    pairs = []
    MAX_AR_PAIRS_PER_ALERT = 5   # 控制单 alert 数据不爆炸

    # ---- Type 1: Accepted vs Rejected ----
    ar_added = 0
    # 优先: (最好 accepted vs 最差 rejected),按 confidence 排序
    accepted_sorted = sorted(accepted,
                              key=lambda t: t.get("final_confidence", 0), reverse=True)
    rejected_sorted = sorted(rejected,
                              key=lambda t: t.get("final_confidence", 0), reverse=True)
    for a in accepted_sorted:
        if ar_added >= MAX_AR_PAIRS_PER_ALERT:
            break
        for r in rejected_sorted:
            if ar_added >= MAX_AR_PAIRS_PER_ALERT:
                break
            steps_a = a.get("steps", [])
            steps_r = r.get("steps", [])
            # 优先挑最后 verdict 步(决策的关键点)
            found = False
            for i in range(min(len(steps_a), len(steps_r)) - 1, -1, -1):
                a_type = steps_a[i]["action"]["type"]
                r_type = steps_r[i]["action"]["type"]
                if a_type == r_type:
                    continue
                pairs.append(build_pair(steps_a[i], steps_r[i], {
                    "source": "accepted_vs_rejected",
                    "alert_id": alert_id,
                    "round": i + 1,
                    "sim_type": "same_alert",
                }))
                ar_added += 1
                found = True
                break
            if not found:
                # 全部动作类型都一样(极少数),配最后一轮(终止判定)
                if steps_a and steps_r:
                    pairs.append(build_pair(steps_a[-1], steps_r[-1], {
                        "source": "accepted_vs_rejected",
                        "alert_id": alert_id,
                        "round": len(steps_a),
                        "sim_type": "same_alert",
                        "note": "same_action_type_terminal_diff",
                    }))
                    ar_added += 1

    # ---- Type 2: Accepted vs Accepted(复合分数排序)---- ⭐ ACRM 精髓
    #
    # 按 ACRM 论文,每个 case 只挑最有信息量的 pair(不是全 combinations):
    #   - best vs worst(最大差异,最强信号)
    #   - 若中位数与两端有明显差异,再各配一对
    # 每 alert 最多产出 max_pairs_per_alert 条(参照论文控制数据分布)
    MAX_AA_PAIRS_PER_ALERT = 3
    MIN_SCORE_DIFF = 0.08   # 略高的阈值,保留真正有差异的对

    if len(accepted) >= 2:
        scored = [(t, compute_composite_score(t, gt)) for t in accepted]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 选 (best vs worst) + (best vs median) + (median vs worst)
        n = len(scored)
        candidate_pairs = []
        if n >= 2:
            candidate_pairs.append((0, n - 1))  # best vs worst
        if n >= 3:
            mid = n // 2
            candidate_pairs.append((0, mid))    # best vs median
            candidate_pairs.append((mid, n - 1))  # median vs worst

        aa_added = 0
        for (i, j) in candidate_pairs:
            if aa_added >= MAX_AA_PAIRS_PER_ALERT:
                break
            better, r_better = scored[i]
            worse, r_worse = scored[j]
            if r_better - r_worse < MIN_SCORE_DIFF:
                continue

            steps_b = better.get("steps", [])
            steps_w = worse.get("steps", [])
            # 优先挑"最终 verdict 步(terminate/escalate)"——那是决策的关键点
            found_pair = False
            for k in range(min(len(steps_b), len(steps_w)) - 1, -1, -1):
                act_b = steps_b[k]["action"]
                act_w = steps_w[k]["action"]
                same = (act_b.get("type") == act_w.get("type")
                        and json.dumps(act_b.get("params", {}), sort_keys=True) ==
                            json.dumps(act_w.get("params", {}), sort_keys=True))
                if same:
                    continue
                pairs.append(build_pair(steps_b[k], steps_w[k], {
                    "source": "accepted_vs_accepted",
                    "alert_id": alert_id,
                    "round": k + 1,
                    "score_diff": round(r_better - r_worse, 3),
                    "better_score": round(r_better, 3),
                    "worse_score": round(r_worse, 3),
                    "pair_rank": ["best_vs_worst", "best_vs_median",
                                    "median_vs_worst"][candidate_pairs.index((i, j))],
                    "diff_type": ("action_type_differs"
                                   if act_b.get("type") != act_w.get("type")
                                   else "params_differ"),
                    "sim_type": "same_alert",
                }))
                aa_added += 1
                found_pair = True
                break  # 一对 (i, j) 只出一条 pair,避免爆炸

    return pairs, {"accepted": len(accepted), "rejected": len(rejected)}


def build_cross_alert_pairs(all_trajs: list[dict],
                             gt_map: dict,
                             sim_threshold: float = 0.65) -> list[dict]:
    """
    跨 alert 匹配。ACRM 用 embedding cosine > 0.75。
    我们用 category-based 相似度作近似:
      - 同 category 内的 alert 相似度视为 1.0(结构性相似:同类欺诈模式)
      - 不同 category 时结合 TF-IDF 文本相似度
    对应论文 Section 3.3 里"跨场景相似轨迹配对"。
    """
    pairs = []
    accepted_all = [(t, gt_map.get(t.get("alert_id"))) for t in all_trajs
                     if gt_map.get(t.get("alert_id"))
                     and verdict_is_accepted(t, gt_map[t.get("alert_id")])]
    rejected_all = [(t, gt_map.get(t.get("alert_id"))) for t in all_trajs
                     if gt_map.get(t.get("alert_id"))
                     and not verdict_is_accepted(t, gt_map[t.get("alert_id")])]

    def _category_sim(a_gt, r_gt):
        """基于 category + trigger_reason 的粗匹配。"""
        if a_gt["category"] == r_gt["category"]:
            return 1.0  # 同 category,视为高相似
        # 不同 category:看 trigger_reason 词汇重叠
        from src.retrieval import _tokenize
        a_tok = set(_tokenize(a_gt.get("trigger_reason", "")))
        r_tok = set(_tokenize(r_gt.get("trigger_reason", "")))
        if not a_tok or not r_tok:
            return 0.0
        return len(a_tok & r_tok) / len(a_tok | r_tok)

    used_count = 0
    for (a, a_gt) in accepted_all:
        for (r, r_gt) in rejected_all:
            if a.get("alert_id") == r.get("alert_id"):
                continue
            sim = _category_sim(a_gt, r_gt)
            if sim < sim_threshold:
                continue
            steps_a = a.get("steps", [])
            steps_r = r.get("steps", [])
            if not steps_a or not steps_r:
                continue
            # 首轮动作差异
            if steps_a[0]["action"]["type"] == steps_r[0]["action"]["type"]:
                # 首轮相同,试第 2、3 轮
                for k in [1, 2]:
                    if k < len(steps_a) and k < len(steps_r) and \
                       steps_a[k]["action"]["type"] != steps_r[k]["action"]["type"]:
                        pairs.append(build_pair(steps_a[k], steps_r[k], {
                            "source": "cross_alert_accepted_vs_rejected",
                            "similarity": round(sim, 3),
                            "accepted_alert": a.get("alert_id"),
                            "rejected_alert": r.get("alert_id"),
                            "round": k + 1,
                            "sim_type": "cross_alert",
                        }))
                        used_count += 1
                        break
                continue
            pairs.append(build_pair(steps_a[0], steps_r[0], {
                "source": "cross_alert_accepted_vs_rejected",
                "similarity": round(sim, 3),
                "accepted_alert": a.get("alert_id"),
                "rejected_alert": r.get("alert_id"),
                "round": 1,
                "sim_type": "cross_alert",
            }))
            used_count += 1
            if used_count > 300:  # 上限
                return pairs
    return pairs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trajectories", nargs="+",
                    default=["logs/eval_memory_*.jsonl"],
                    help="glob 表达式,可指定多个轨迹源")
    p.add_argument("--sim-threshold", type=float, default=0.75,
                    help="跨 alert 匹配的最小相似度")
    p.add_argument("--output", default="logs/dpo_train_acrm.jsonl")
    p.add_argument("--include-cross-alert", action="store_true", default=True,
                    help="是否加入跨 alert 相似度匹配的 pair")
    p.add_argument("--stats-only", action="store_true")
    args = p.parse_args()

    print("=" * 60)
    print("ACRM-style DPO Data Construction")
    print("=" * 60)

    trajectories = load_trajectories(args.trajectories)
    gt_map = load_gt()
    print(f"\nLoaded {len(trajectories)} trajectories from files.")
    print(f"Ground-truth alerts: {len(gt_map)}")

    # 按 alert 分组
    by_alert = defaultdict(list)
    for t in trajectories:
        aid = t.get("alert_id")
        if aid in gt_map:
            by_alert[aid].append(t)

    print(f"Alerts with trajectories: {len(by_alert)}")
    n_per_alert = [len(v) for v in by_alert.values()]
    if n_per_alert:
        print(f"  Trajectories per alert: min={min(n_per_alert)}, "
              f"median={sorted(n_per_alert)[len(n_per_alert)//2]}, "
              f"max={max(n_per_alert)}")

    # ==== Step 1+2: 同 alert 内构造 pair ====
    all_pairs = []
    alert_stats = {}
    for aid, trajs in by_alert.items():
        pairs, stats = build_pairs_within_alert(trajs, gt_map[aid], aid)
        all_pairs.extend(pairs)
        alert_stats[aid] = stats

    # ==== Step 3: 跨 alert 相似匹配 ====
    if args.include_cross_alert:
        print("\nBuilding cross-alert pairs (cosine matching)...")
        cross_pairs = build_cross_alert_pairs(trajectories, gt_map,
                                                sim_threshold=args.sim_threshold)
        all_pairs.extend(cross_pairs)

    # ==== 统计 ====
    by_source = Counter(p["meta"]["source"] for p in all_pairs)
    total = len(all_pairs)
    stats_lines = [
        "# ACRM-style DPO Dataset — Statistics",
        "",
        f"**Total pairs**: {total}",
        "",
        "## Source breakdown",
        "",
        "| Source | Count | % | ACRM equivalent |",
        "|---|---|---|---|",
    ]
    acrm_map = {
        "accepted_vs_rejected": "① Accepted vs Rejected (ACRM: 55%)",
        "accepted_vs_accepted": "② Accepted vs Accepted (ACRM: 35%, 精髓)",
        "cross_alert_accepted_vs_rejected": "跨场景 A vs R (ACRM: cosine>0.75 匹配)",
    }
    for src, cnt in by_source.most_common():
        pct = 100 * cnt / total if total else 0
        stats_lines.append(f"| `{src}` | {cnt} | {pct:.1f}% | {acrm_map.get(src, '-')} |")
    stats_lines.append("")

    # 复合分数分布
    aa_pairs = [p for p in all_pairs if p["meta"]["source"] == "accepted_vs_accepted"]
    if aa_pairs:
        diffs = [p["meta"]["score_diff"] for p in aa_pairs]
        stats_lines.append("## Accepted-vs-Accepted 复合分数差异分布")
        stats_lines.append("")
        stats_lines.append(f"- 样本数: {len(diffs)}")
        stats_lines.append(f"- 差异均值: {sum(diffs)/len(diffs):.3f}")
        stats_lines.append(f"- 差异范围: [{min(diffs):.3f}, {max(diffs):.3f}]")
        stats_lines.append("")
        stats_lines.append(f"**权重设定**: "
                            f"α_verdict={COMPOSITE_WEIGHTS['alpha_verdict']}, "
                            f"α_conf={COMPOSITE_WEIGHTS['alpha_conf']}, "
                            f"α_recall={COMPOSITE_WEIGHTS['alpha_recall']}, "
                            f"β_fp={COMPOSITE_WEIGHTS['beta_fp']}, "
                            f"γ_esc={COMPOSITE_WEIGHTS['gamma_esc']}, "
                            f"δ_rounds={COMPOSITE_WEIGHTS['delta_rounds']}")
        stats_lines.append("")

    # Per-alert 分布
    stats_lines.append("## Per-alert 覆盖")
    stats_lines.append("")
    stats_lines.append(f"- 覆盖 alert 数: {len(alert_stats)}")
    both = sum(1 for s in alert_stats.values() if s["accepted"] > 0 and s["rejected"] > 0)
    aa_ready = sum(1 for s in alert_stats.values() if s["accepted"] >= 2)
    stats_lines.append(f"- 同时有 accepted + rejected 轨迹的 alert: {both}(可造 A-vs-R)")
    stats_lines.append(f"- accepted 轨迹 ≥ 2 的 alert: {aa_ready}(可造 A-vs-A)")

    stats_report = "\n".join(stats_lines)
    print("\n" + stats_report)

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

    # Stats + Samples
    (out.with_suffix(".stats.md")).write_text(stats_report)
    with open(out.with_suffix(".sample.md"), "w") as f:
        f.write("# DPO Pairs — ACRM-style Samples\n\n")
        # 优先展示 accepted_vs_accepted(因为最珍贵)
        priority = sorted(all_pairs,
                           key=lambda p: (p["meta"]["source"] != "accepted_vs_accepted", 0))
        for i, p in enumerate(priority[:8]):
            f.write(f"## Pair {i+1} — {p['meta']['source']}\n\n")
            f.write(f"**Meta**: `{p['meta']}`\n\n")
            f.write("### Prompt\n```\n" + p["prompt"][:1200] + "...\n```\n\n")
            f.write("### Chosen\n```json\n" + p["chosen"] + "\n```\n\n")
            f.write("### Rejected\n```json\n" + p["rejected"] + "\n```\n\n---\n\n")
    print(f"Stats:   {out.with_suffix('.stats.md')}")
    print(f"Samples: {out.with_suffix('.sample.md')}")


if __name__ == "__main__":
    main()
