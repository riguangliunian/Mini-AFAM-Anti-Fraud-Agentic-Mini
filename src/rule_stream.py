"""
Rule Stream:反欺诈领域的硬约束护栏。

对应 ACRM 论文 Section 3.3 的 Rule Stream。
关键差异(反欺诈 vs 信用风险):
- 信用风险护栏是 PSI/KS(稳定性)
- 反欺诈护栏是 误伤率/覆盖度/延迟/合规
"""

from dataclasses import dataclass
from typing import Optional
from .state import Action, State


@dataclass
class Violation:
    rule_name: str
    message: str


class RuleStream:
    """
    生成-验证循环里的 Validator。
    输入:候选 Action + 当前 State
    输出:None(通过)或 Violation(带错误信息用于 re-prompt)
    """

    # 硬约束参数(反欺诈场景)
    MAX_ESTIMATED_FP_RATE = 0.005  # 好用户误伤率上限 0.5%
    MIN_RULE_COVERAGE = 3  # 单规则最少覆盖 3 个 case(demo 数据小,生产应设 100)
    MAX_FEATURE_P99_LATENCY_MS = 100
    MIN_LABEL_MATURITY_FOR_HIGH_CONFIDENCE = 0.5  # 标签成熟度 < 0.5 时不允许直接下结论
    MIN_RETRIEVAL_CONFIDENCE = 0.55  # 检索置信度 < 该阈值视为新型模式
    MAX_GRAPH_HOP = 2  # 图查询最多两跳
    MAX_SHADOW_REPLAY_DAYS = 30
    FORBIDDEN_DATA_SOURCES = ["contacts_without_consent", "phone_call_records_raw"]

    def validate(self, action: Action, state: State) -> Optional[Violation]:
        """按动作类型分派校验。"""
        checker = getattr(self, f"_check_{action.action_type}", None)
        if checker:
            return checker(action, state)
        return None

    # ===== 各动作的具体校验 =====

    def _check_expand_neighbors(self, action: Action, state: State) -> Optional[Violation]:
        hop = action.params.get("hop", 1)
        if hop > self.MAX_GRAPH_HOP:
            return Violation(
                "MAX_HOP_EXCEEDED",
                f"Rejected: hop={hop} exceeds MAX_GRAPH_HOP={self.MAX_GRAPH_HOP}. "
                f"Graph queries beyond 2-hop exceed 100ms latency budget. Revise."
            )
        edge_type = action.params.get("edge_type", "")
        if edge_type == "contact" and hop >= 2 and state.round_num <= 1:
            return Violation(
                "PRIVACY_GUARD",
                "Rejected: 2-hop contact expansion at round 0 lacks consent scope. "
                "Start with 1-hop device/ip expansion first."
            )
        return None

    def _check_generate_rule(self, action: Action, state: State) -> Optional[Violation]:
        if not state.pattern_assessment.get("eligible", False):
            return Violation(
                "PATTERN_NOT_REUSABLE",
                "Rejected: evidence supports at most a case decision, not a reusable group rule. "
                "Continue investigation, terminate the case, or escalate for human review."
            )
        pattern = action.params.get("pattern", "")
        coverage = action.params.get("coverage_min", 0)

        # 结构 + 属性组合校验(避免"仅共享 WiFi"导致的邻居误伤)
        has_structure_signal = any(kw in pattern.lower() for kw in
                                    ["shared_", "device", "ip", "contact", "gps", "graph"])
        has_attribute_signal = any(kw in pattern.lower() for kw in
                                    ["new_account", "age", "amount", "night", "speed",
                                     "paste", "black_list"])
        if not has_structure_signal or not has_attribute_signal:
            return Violation(
                "INCOMPLETE_RULE_EVIDENCE",
                f"Rejected: rule pattern must combine structure and attribute evidence ({pattern!r}). "
                "Add at least one structure signal (shared_device/ip/contact) and one "
                "attribute signal (new_account/night/etc) "
                "to avoid neighbor false-positives (e.g. WiFi-sharing residents)."
            )
        if coverage < self.MIN_RULE_COVERAGE:
            return Violation(
                "COVERAGE_TOO_LOW",
                f"Rejected: coverage_min={coverage} below MIN_RULE_COVERAGE={self.MIN_RULE_COVERAGE}. "
                "Rule may be overfitting to individual cases."
            )
        return None

    def _check_adversarial_probe(self, action: Action, state: State) -> Optional[Violation]:
        if not state.pattern_assessment.get("eligible", False):
            return Violation(
                "PATTERN_NOT_REUSABLE",
                "Rejected: current case has not passed the reusable-pattern gate. "
                "Finish case investigation or escalate; do not run deployment validation."
            )
        return None

    def _check_terminate(self, action: Action, state: State) -> Optional[Violation]:
        verdict = action.params.get("verdict", "")
        confidence = action.params.get("confidence", 0.0)

        # 标签成熟度守护:低成熟度不允许高置信度直接定案
        if (verdict == "fraud_confirmed"
                and confidence > 0.8
                and state.label_maturity < self.MIN_LABEL_MATURITY_FOR_HIGH_CONFIDENCE):
            return Violation(
                "LABEL_MATURITY_GUARD",
                f"Rejected: high confidence ({confidence}) with immature labels "
                f"(maturity={state.label_maturity:.2f} < 0.5). "
                "Downgrade confidence, or escalate_to_human, or recommend 30-day recheck."
            )
        # 检索置信度低时不允许 auto-confirm
        if verdict == "fraud_confirmed" and state.retrieval_confidence < self.MIN_RETRIEVAL_CONFIDENCE:
            return Violation(
                "NOVEL_PATTERN_GUARD",
                f"Rejected: retrieval_confidence={state.retrieval_confidence:.2f} "
                f"< {self.MIN_RETRIEVAL_CONFIDENCE} suggests novel attack pattern. "
                "Use escalate_to_human instead of auto-terminate."
            )
        return None

    def _check_shadow_replay(self, action: Action, state: State) -> Optional[Violation]:
        if not state.pattern_assessment.get("eligible", False):
            return Violation(
                "PATTERN_NOT_REUSABLE",
                "Rejected: only reusable-pattern candidates may enter deployment replay."
            )
        days = action.params.get("replay_days", 0)
        if days > self.MAX_SHADOW_REPLAY_DAYS:
            return Violation(
                "REPLAY_WINDOW_EXCEEDED",
                f"Rejected: replay_days={days} > {self.MAX_SHADOW_REPLAY_DAYS}. "
                "Older data may reflect deprecated attack patterns."
            )
        return None
