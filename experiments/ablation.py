"""
Day 6:消融实验。

对照 4 种配置:
1. Full Mini-AFAM         三流全开
2. No-Retrieval           关掉检索(只用规则 + 对齐)
3. No-Alignment           关掉偏好提示(只用规则 + 检索)
4. Rule-Only              只用规则(既没检索也没对齐)

评估指标(反欺诈版,对应 ACRM Table 3):
- Recall:欺诈告警被正确 fraud_confirmed 的比例
- FP-rate:非欺诈告警被误判 fraud_confirmed 的比例
- Rounds:平均调查轮数
- Escalate-rate:被 escalate_to_human 的比例
- Rule-violations:被 Rule Stream 拒绝的次数(反映探索质量)

用法:
    LLM_MODEL=mock python -m experiments.ablation
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tabulate import tabulate

from src.memory import TrajectoryMemory
from src.orchestrator import Orchestrator, OrchestratorConfig

DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"


CONFIGS = {
    "Full AFAM":       OrchestratorConfig(use_retrieval=True, use_alignment=True, use_rules=True, log_verbose=False),
    "No-Retrieval":    OrchestratorConfig(use_retrieval=False, use_alignment=True, use_rules=True, log_verbose=False),
    "No-Alignment":    OrchestratorConfig(use_retrieval=True, use_alignment=False, use_rules=True, log_verbose=False),
    "Rule-Only":       OrchestratorConfig(use_retrieval=False, use_alignment=False, use_rules=True, log_verbose=False),
    "No-Rules":        OrchestratorConfig(use_retrieval=True, use_alignment=True, use_rules=False, log_verbose=False),
}


@dataclass
class Metrics:
    total: int = 0
    tp: int = 0  # true fraud → fraud_confirmed
    fp: int = 0  # normal → fraud_confirmed
    fn: int = 0  # true fraud → not_fraud (missed)
    tn: int = 0  # normal → not_fraud
    escalate: int = 0
    total_rounds: int = 0
    total_time: float = 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def fp_rate(self) -> float:
        d = self.fp + self.tn
        return self.fp / d if d else 0.0

    @property
    def avg_rounds(self) -> float:
        return self.total_rounds / self.total if self.total else 0.0

    @property
    def escalate_rate(self) -> float:
        return self.escalate / self.total if self.total else 0.0


def _true_label_for_alert(alert: dict) -> str:
    """从 alert 的 note / 数据推断 ground truth。"""
    if "false-positive" in (alert.get("note") or "").lower():
        return "normal"
    return "fraud"


def _classify(verdict: str, true_label: str, m: Metrics):
    m.total += 1
    if verdict == "escalate":
        m.escalate += 1
        return
    predicted_fraud = verdict == "fraud_confirmed"
    if true_label == "fraud":
        if predicted_fraud:
            m.tp += 1
        else:
            m.fn += 1
    else:
        if predicted_fraud:
            m.fp += 1
        else:
            m.tn += 1


def run_config(name: str, config: OrchestratorConfig, alerts: list[dict]) -> Metrics:
    # 每种配置用独立的内存空间,避免相互污染
    memory_path = LOGS_DIR / f"memory_{name.replace(' ', '_').replace('-', '_')}.jsonl"
    if memory_path.exists():
        memory_path.unlink()
    memory = TrajectoryMemory(path=memory_path)
    orch = Orchestrator(config=config, memory=memory)

    m = Metrics()
    for alert in alerts:
        traj = orch.investigate(alert)
        _classify(traj.verdict or "escalate", _true_label_for_alert(alert), m)
        m.total_rounds += len(traj.steps)
        m.total_time += traj.total_seconds
    return m


def main():
    with open(DATA_DIR / "alerts.json") as f:
        alerts = json.load(f)

    print(f"Running ablation on {len(alerts)} alerts × {len(CONFIGS)} configs = "
          f"{len(alerts) * len(CONFIGS)} investigations\n")

    results = {}
    for name, config in CONFIGS.items():
        print(f"  Running {name}...", end=" ", flush=True)
        results[name] = run_config(name, config, alerts)
        print("done")

    # 表格输出
    print("\n\n=========== Ablation results ============\n")
    rows = []
    for name, m in results.items():
        rows.append([
            name,
            f"{m.recall:.0%}",
            f"{m.fp_rate:.0%}",
            f"{m.escalate_rate:.0%}",
            f"{m.avg_rounds:.1f}",
            f"{m.total_time:.2f}s",
        ])
    print(tabulate(
        rows,
        headers=["Config", "Recall", "FP-rate", "Escalate%", "Avg Rounds", "Total Time"],
        tablefmt="github",
    ))

    # 差异解读
    full = results["Full AFAM"]
    print("\n=========== Key takeaways ============\n")
    for name in ["No-Retrieval", "No-Alignment", "Rule-Only", "No-Rules"]:
        m = results[name]
        delta_rounds = m.avg_rounds - full.avg_rounds
        delta_recall = m.recall - full.recall
        delta_fp = m.fp_rate - full.fp_rate
        parts = []
        if abs(delta_rounds) > 0.1:
            parts.append(f"rounds {'↑' if delta_rounds>0 else '↓'}{abs(delta_rounds):.1f}")
        if abs(delta_recall) > 0.01:
            parts.append(f"recall {'↓' if delta_recall<0 else '↑'}{abs(delta_recall):.0%}")
        if abs(delta_fp) > 0.01:
            parts.append(f"FP {'↑' if delta_fp>0 else '↓'}{abs(delta_fp):.0%}")
        if not parts:
            parts.append("no significant change")
        print(f"  {name}: {', '.join(parts)}")

    # 保存结果 JSON
    out = {name: {
        "recall": m.recall, "fp_rate": m.fp_rate,
        "escalate_rate": m.escalate_rate, "avg_rounds": m.avg_rounds,
        "tp": m.tp, "fp": m.fp, "tn": m.tn, "fn": m.fn, "escalate": m.escalate,
    } for name, m in results.items()}
    out_path = LOGS_DIR / "ablation_results.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()
