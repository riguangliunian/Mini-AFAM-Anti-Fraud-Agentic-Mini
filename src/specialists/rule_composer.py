"""
RuleComposer:根据当前证据生成拦截规则。

设计:
- 输入:诊断报告 + 关键实体
- 输出:结构化规则(pattern + 阈值 + 覆盖范围估计)
- 组合结构信号 + 属性信号,避免"仅共享 WiFi"这类误伤
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Rule:
    rule_id: str
    pattern: str  # 自然语言描述
    conditions: list[dict[str, Any]] = field(default_factory=list)
    coverage_est: int = 0
    fp_rate_est: float = 0.0

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "pattern": self.pattern,
            "conditions": self.conditions,
            "coverage_est": self.coverage_est,
            "fp_rate_est": self.fp_rate_est,
        }


class RuleComposer:
    """
    根据 diagnostic report + LLM 建议合成规则。
    demo 简化:直接从诊断信息提取显性组合,不真调 LLM。
    """

    _counter = 0

    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"rule_{cls._counter:03d}"

    def compose_from_diagnostic(self,
                                 diagnostic: dict,
                                 suspect_users: list[str],
                                 df=None) -> Rule:
        """基于诊断结果自动组合一条规则。"""
        conditions = []

        # 结构信号
        shared = diagnostic.get("shared_entities", {})
        if shared.get("device_id"):
            top = shared["device_id"][0]
            conditions.append({
                "type": "shared_entity",
                "entity_type": "device_id",
                "min_shared_users": 3,
                "note": f"e.g. device '{top['entity']}' shared by {top['count']} users",
            })
        elif shared.get("ip"):
            top = shared["ip"][0]
            conditions.append({
                "type": "shared_entity",
                "entity_type": "ip",
                "min_shared_users": 3,
                "note": f"e.g. ip '{top['entity']}' shared by {top['count']} users",
            })
        elif shared.get("contact"):
            top = shared["contact"][0]
            conditions.append({
                "type": "shared_entity",
                "entity_type": "contact",
                "min_shared_users": 3,
                "note": f"e.g. contact '{top['entity']}' shared by {top['count']} users",
            })

        # 属性信号(硬要求:必须有至少一个)
        metrics = diagnostic.get("metrics", {})
        if metrics.get("new_account_ratio", 0) > 0.5:
            conditions.append({
                "type": "attribute",
                "field": "is_new_account",
                "op": "==",
                "value": True,
                "note": f"suspect group new_account_ratio={metrics['new_account_ratio']:.0%}"
            })
        if metrics.get("night_apply_ratio", 0) > 0.3:
            conditions.append({
                "type": "attribute",
                "field": "night_apply",
                "op": "==",
                "value": True,
            })
        # 兜底属性信号
        if not any(c["type"] == "attribute" for c in conditions):
            conditions.append({
                "type": "attribute",
                "field": "account_age_days",
                "op": "<=",
                "value": 30,
                "note": "fallback: new-ish account",
            })

        # 时间聚集
        if diagnostic.get("burst", {}).get("burst_detected"):
            conditions.append({
                "type": "temporal_burst",
                "window_hours": diagnostic["burst"]["window_hours"],
                "min_apps_in_window": 3,
            })

        pattern = " AND ".join([self._cond_repr(c) for c in conditions])

        rule = Rule(
            rule_id=self._next_id(),
            pattern=pattern,
            conditions=conditions,
        )
        # 用 df 估算覆盖和误伤
        if df is not None:
            hits = self._simulate_hits(rule, df)
            rule.coverage_est = int(hits["true_positive"] + hits["false_positive"])
            rule.fp_rate_est = float(hits["fp_rate"])
        return rule

    def _cond_repr(self, c: dict) -> str:
        if c["type"] == "shared_entity":
            return f"shared_{c['entity_type']}>={c['min_shared_users']}"
        if c["type"] == "attribute":
            return f"{c['field']}{c['op']}{c['value']}"
        if c["type"] == "temporal_burst":
            return f"burst_{c['window_hours']}h>={c['min_apps_in_window']}"
        return str(c)

    def _simulate_hits(self, rule: Rule, df) -> dict:
        """在合成数据上快速估算规则命中的召回/误伤。"""
        # 简化实现:只用属性条件筛选,shared_entity 走全表统计
        mask = df["user_id"].notna()
        for c in rule.conditions:
            if c["type"] == "attribute":
                col = c["field"]
                op = c["op"]
                val = c["value"]
                if col not in df.columns:
                    continue
                if op == "==":
                    mask &= (df[col] == val)
                elif op == "<=":
                    mask &= (df[col] <= val)
                elif op == ">=":
                    mask &= (df[col] >= val)

        hit = df[mask]
        tp = int((hit["true_label"] == "fraud").sum())
        fp = int((hit["true_label"] == "normal").sum())
        total_normal = int((df["true_label"] == "normal").sum())
        fp_rate = fp / max(total_normal, 1)
        return {"true_positive": tp, "false_positive": fp, "fp_rate": fp_rate,
                "hit_count": len(hit)}
