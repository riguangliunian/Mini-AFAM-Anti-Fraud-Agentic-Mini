"""
AdversarialProber:红队 Agent,主动尝试绕过新生成的规则。

反欺诈独有,ACRM 完全没有的维度。
每次生成规则后跑一遍,发现绕过路径就补规则。
"""

from typing import Any
from .rule_composer import Rule


class AdversarialProber:
    """
    尝试常见绕过手段,看新规则是否能防住。
    demo 版:枚举 5 种典型绕过策略,看规则条件是否被覆盖。
    """

    BYPASS_STRATEGIES = [
        {
            "name": "device_rotation",
            "description": "攻击者换设备指纹",
            "breaks_condition_type": "shared_device_id",
        },
        {
            "name": "ip_rotation",
            "description": "攻击者使用 IP 池",
            "breaks_condition_type": "shared_ip",
        },
        {
            "name": "amount_split",
            "description": "拆分金额到多次小额申请",
            "breaks_condition_type": "amount_threshold",
        },
        {
            "name": "delayed_apply",
            "description": "拉长申请间隔避开时间窗",
            "breaks_condition_type": "temporal_burst",
        },
        {
            "name": "aged_account",
            "description": "用养号绕过 is_new_account 限制",
            "breaks_condition_type": "is_new_account",
        },
    ]

    def probe(self, rule: Rule) -> dict[str, Any]:
        """
        返回:{
            "bypass_findings": [{strategy, can_bypass, reason}],
            "verdict": "robust" | "has_gaps" | "trivially_bypassable"
        }
        """
        findings = []
        for strat in self.BYPASS_STRATEGIES:
            can_bypass = self._can_bypass(rule, strat)
            findings.append({
                "strategy": strat["name"],
                "description": strat["description"],
                "can_bypass": can_bypass,
                "reason": self._explain(rule, strat, can_bypass),
            })

        bypass_count = sum(1 for f in findings if f["can_bypass"])
        if bypass_count == 0:
            verdict = "robust"
        elif bypass_count <= 2:
            verdict = "has_gaps"
        else:
            verdict = "trivially_bypassable"

        return {
            "rule_id": rule.rule_id,
            "bypass_findings": findings,
            "bypass_count": bypass_count,
            "verdict": verdict,
        }

    def _can_bypass(self, rule: Rule, strat: dict) -> bool:
        """
        判断:该绕过策略是否能规避 rule 里的所有条件。
        规则如果只有单一维度条件,大多数绕过都能生效。
        规则如果有多维组合,单一绕过策略往往不够。
        """
        # 提取规则触碰的条件类型
        touched_types = set()
        for c in rule.conditions:
            if c["type"] == "shared_entity":
                touched_types.add(f"shared_{c['entity_type']}")
            elif c["type"] == "attribute":
                touched_types.add(c["field"])
            elif c["type"] == "temporal_burst":
                touched_types.add("temporal_burst")

        # 该绕过策略破坏的条件类型
        broken = strat["breaks_condition_type"]

        # 如果规则的所有条件都能被这一个策略破坏,则可绕过
        # 简化判定:该绕过破坏的类型 ∈ 规则条件,且规则条件数量 <=1 时最脆弱
        if broken not in touched_types:
            return False  # 该策略跟规则不相关
        # 触碰到的条件数量 = 1(单一条件)→ 可绕过
        return len(touched_types) <= 1

    def _explain(self, rule: Rule, strat: dict, can_bypass: bool) -> str:
        if can_bypass:
            return (f"Rule relies on {strat['breaks_condition_type']} alone; "
                    f"attacker can {strat['description']}.")
        return f"Rule combines multiple conditions; {strat['name']} alone insufficient."
