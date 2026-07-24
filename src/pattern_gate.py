"""候选规则生产门控。

把“当前案件是否为欺诈”和“当前证据是否足以抽象成可复用规则”分开。
该模块只做确定性证据汇总，不替代人工审批或最终上线决策。
"""

from dataclasses import dataclass, asdict

from .state import State, Trajectory


@dataclass
class PatternAssessment:
    eligible: bool
    score: float
    evidence_families: int
    group_support: float
    multi_signal: float
    consistency: float
    label_maturity: float
    precedent: float
    tool_integrity: float
    deployment_mode: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class PatternEligibilityGate:
    """判断是否允许从个案进入候选规则生产分支。"""

    MIN_SCORE = 0.60
    MIN_SUSPECTS = 3
    MIN_EVIDENCE_FAMILIES = 2

    def assess(self, state: State, traj: Trajectory) -> PatternAssessment:
        fp = state.graph_fingerprint or {}
        suspect_count = len(state.suspect_set)
        group_support = min(suspect_count / 5.0, 1.0)

        structure = bool(fp.get("shared_entity_types"))
        temporal = bool(fp.get("burst"))
        behavior = any([
            state.key_metrics.get("new_account_ratio", 0) > 0.5,
            state.key_metrics.get("night_apply_ratio", 0) > 0.3,
            state.key_metrics.get("paste_used_ratio", 0) > 0.3,
        ])
        evidence_families = sum([structure, temporal, behavior])
        multi_signal = min(evidence_families / 2.0, 1.0)

        ratios = [
            state.key_metrics.get("new_account_ratio", 0.0),
            state.key_metrics.get("night_apply_ratio", 0.0),
            state.key_metrics.get("paste_used_ratio", 0.0),
        ]
        active_ratios = [r for r in ratios if r > 0.3]
        consistency = sum(active_ratios) / len(active_ratios) if active_ratios else 0.0
        maturity = max(0.0, min(float(state.label_maturity), 1.0))
        precedent = max(0.0, min(float(state.retrieval_confidence), 1.0))
        tool_integrity = 1.0 if all(s.outcome.success for s in traj.steps) else 0.0

        score = (
            0.25 * group_support
            + 0.25 * multi_signal
            + 0.20 * consistency
            + 0.15 * maturity
            + 0.15 * precedent
        ) * tool_integrity
        score = round(score, 3)

        reasons = []
        if suspect_count < self.MIN_SUSPECTS:
            reasons.append(f"insufficient group support: {suspect_count} < {self.MIN_SUSPECTS}")
        if evidence_families < self.MIN_EVIDENCE_FAMILIES:
            reasons.append(
                f"insufficient independent evidence families: {evidence_families} < {self.MIN_EVIDENCE_FAMILIES}"
            )
        if tool_integrity == 0:
            reasons.append("trajectory contains failed tool outcomes")
        if score < self.MIN_SCORE:
            reasons.append(f"pattern score {score:.3f} < {self.MIN_SCORE:.2f}")

        eligible = not reasons
        if not eligible:
            deployment_mode = "case_only"
        elif precedent < 0.55 or maturity < 0.5:
            deployment_mode = "shadow_human_review"
        else:
            deployment_mode = "candidate_rule"

        return PatternAssessment(
            eligible=eligible,
            score=score,
            evidence_families=evidence_families,
            group_support=round(group_support, 3),
            multi_signal=round(multi_signal, 3),
            consistency=round(consistency, 3),
            label_maturity=round(maturity, 3),
            precedent=round(precedent, 3),
            tool_integrity=tool_integrity,
            deployment_mode=deployment_mode,
            reasons=reasons,
        )
