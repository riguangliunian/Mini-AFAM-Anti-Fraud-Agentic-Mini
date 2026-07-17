"""
生成结构化评测集,附带 ground truth。

产出:data/eval_alerts.json
每条告警含:
  - alert_id, seed_user, trigger_reason, severity
  - category: A/B/C/D/E/F
  - difficulty: easy/medium/hard
  - expected_verdict: fraud_confirmed / not_fraud / escalate
  - alt_ok_verdicts: 可接受的备选(如 B 类可以 escalate 也可 conf 低的 fraud_confirmed)
  - expected_confidence_range: [min, max]
  - test_point: 一句话解释这条测的是什么

前提:先跑 data/generate_data.py。
额外造几组独立 pattern(养号团伙、孤立用户、novel 模式的 seed)。
"""

import json
import pickle
import random
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent
SEED = 20260717  # 与训练不同的 seed 保证覆盖
random.seed(SEED)
np.random.seed(SEED)


def _load():
    df = pd.read_parquet(DATA_DIR / "graph_data.parquet")
    with open(DATA_DIR / "entity_graph.pkl", "rb") as f:
        G = pickle.load(f)
    return df, G


def _pick_gang_seeds(df, G, tag_prefix: str, n: int) -> list[str]:
    """从某类团伙里挑度数最高的 n 个作为不同告警的 seed。"""
    gang_users = df[df["group_tag"].str.startswith(tag_prefix)]["user_id"].tolist()
    if not gang_users:
        return []
    scored = [(u, G.degree(u)) for u in gang_users if u in G]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [u for u, _ in scored[:n]]


def _pick_wifi_seeds(df, G, n: int) -> list[str]:
    """从 WiFi 邻居组里挑 n 个 seed。"""
    wifi_users = df[df["group_tag"].str.startswith("wifi_neighborhood_")]["user_id"].tolist()
    scored = [(u, G.degree(u)) for u in wifi_users if u in G]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [u for u, _ in scored[:n]]


def _pick_isolated_normal(df, G, n: int) -> list[str]:
    """挑真正孤立的正常用户(低度数,标签成熟)。"""
    normal_users = df[(df["true_label"] == "normal")
                       & (df["label_maturity"] > 0.8)
                       & (~df["group_tag"].str.startswith("wifi_"))]["user_id"].tolist()
    scored = [(u, G.degree(u)) for u in normal_users if u in G]
    scored.sort(key=lambda x: x[1])  # 低度数
    return [u for u, _ in scored[:n]]


def generate_eval_alerts():
    df, G = _load()

    alerts = []
    base_ts = int(df["timestamp"].mean())

    # ===== A. 明显团伙 (8 alerts) =====
    obvious_seeds = _pick_gang_seeds(df, G, "gang_obvious_", 8)
    for i, seed in enumerate(obvious_seeds):
        trigger_options = [
            "Device shared by 8+ users within 24h",
            "Multiple new accounts from same IP + device",
            "Burst of applications from single device fingerprint",
        ]
        alerts.append({
            "alert_id": f"eval_A{i:02d}",
            "seed_user": seed,
            "trigger_reason": trigger_options[i % len(trigger_options)],
            "severity": "high",
            "category": "A_obvious_gang",
            "difficulty": "easy",
            "expected_verdict": "fraud_confirmed",
            "alt_ok_verdicts": [],
            "expected_confidence_range": [0.75, 1.0],
            "test_point": "Basic gang detection with obvious device/IP sharing",
        })

    # ===== B. 微妙团伙 + 标签不成熟 (6 alerts) =====
    subtle_seeds = _pick_gang_seeds(df, G, "gang_subtle_", 6)
    for i, seed in enumerate(subtle_seeds):
        alerts.append({
            "alert_id": f"eval_B{i:02d}",
            "seed_user": seed,
            "trigger_reason": "Contact overlap detected among small user group",
            "severity": "medium",
            "category": "B_subtle_immature",
            "difficulty": "hard",
            "expected_verdict": "fraud_confirmed",
            "alt_ok_verdicts": ["escalate"],
            "expected_confidence_range": [0.4, 0.75],
            "test_point": "Label-maturity guard: subtle gang with immature labels — expect either downgraded confidence or escalate",
        })

    # ===== C. WiFi 邻居误报 (6 alerts) =====
    wifi_seeds = _pick_wifi_seeds(df, G, 6)
    for i, seed in enumerate(wifi_seeds):
        alerts.append({
            "alert_id": f"eval_C{i:02d}",
            "seed_user": seed,
            "trigger_reason": "IP shared by 8+ users flagged by rule engine",
            "severity": "medium",
            "category": "C_wifi_false_positive",
            "difficulty": "medium",
            "expected_verdict": "not_fraud",
            "alt_ok_verdicts": ["escalate"],  # 谨慎升级也算可接受
            "expected_confidence_range": [0.5, 1.0],
            "test_point": "Structure-only rule guard: shared IP but mature accounts, high age — should NOT be flagged as fraud",
        })

    # ===== D. 孤立正常用户 (6 alerts) =====
    isolated = _pick_isolated_normal(df, G, 6)
    for i, seed in enumerate(isolated):
        alerts.append({
            "alert_id": f"eval_D{i:02d}",
            "seed_user": seed,
            "trigger_reason": "Anomaly detector flagged high-amount application",
            "severity": "low",
            "category": "D_isolated_normal",
            "difficulty": "easy",
            "expected_verdict": "not_fraud",
            "alt_ok_verdicts": ["escalate"],
            "expected_confidence_range": [0.5, 1.0],
            "test_point": "Isolated normal user: 1-hop expand returns nothing suspicious",
        })

    # ===== E. 新型模式 (4 alerts) =====
    # 用 subtle gang seed 但配上"没见过的 trigger",构造新型模式
    novel_seeds = _pick_gang_seeds(df, G, "gang_subtle_", 4)[-4:]
    if len(novel_seeds) < 4:
        novel_seeds = obvious_seeds[-4:] if len(obvious_seeds) >= 4 else obvious_seeds
    for i, seed in enumerate(novel_seeds):
        alerts.append({
            "alert_id": f"eval_E{i:02d}",
            "seed_user": seed,
            "trigger_reason": "Cross-border payment velocity anomaly in unprecedented geographic cluster",
            "severity": "high",
            "category": "E_novel_pattern",
            "difficulty": "hard",
            "expected_verdict": "escalate",
            "alt_ok_verdicts": [],
            "expected_confidence_range": [0.0, 0.5],
            "test_point": "Retrieval-confidence guard: novel trigger phrasing should escalate rather than auto-confirm",
        })

    # ===== F. 抗规避:多样 seed 检查 rule composition =====
    # 从明显团伙里挑不同 seed,期望 rule 能防不同的绕过
    if len(obvious_seeds) >= 4:
        for i, seed in enumerate(obvious_seeds[-4:]):
            alerts.append({
                "alert_id": f"eval_F{i:02d}",
                "seed_user": seed,
                "trigger_reason": "Device shared + suspicious behavior spike",
                "severity": "high",
                "category": "F_rule_robustness",
                "difficulty": "medium",
                "expected_verdict": "fraud_confirmed",
                "alt_ok_verdicts": ["escalate"],
                "expected_confidence_range": [0.6, 1.0],
                "test_point": "Adversarial-prober should verify multi-condition rule; single-condition rules should be rejected",
            })

    out_path = DATA_DIR / "eval_alerts.json"
    with open(out_path, "w") as f:
        json.dump({"total": len(alerts), "alerts": alerts}, f, indent=2, ensure_ascii=False)

    # 打印摘要
    print(f"Generated {len(alerts)} eval alerts, saved to {out_path}")
    from collections import Counter
    by_cat = Counter(a["category"] for a in alerts)
    by_diff = Counter(a["difficulty"] for a in alerts)
    by_exp = Counter(a["expected_verdict"] for a in alerts)
    print(f"\nBy category:  {dict(by_cat)}")
    print(f"By difficulty: {dict(by_diff)}")
    print(f"By expected verdict: {dict(by_exp)}")


if __name__ == "__main__":
    generate_eval_alerts()
