"""
ShadowEvaluator:在历史/合成流量上回放新规则,评估召回和误伤。

这是反欺诈独有的 Agent(ACRM 不需要)。
在真实环境里,shadow 是在生产流量镜像上跑,demo 用合成数据 replay。
"""

from pathlib import Path
import pandas as pd

from .rule_composer import Rule

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class ShadowEvaluator:
    """
    在历史数据上评估规则的召回率、误伤率、覆盖数。
    """

    def __init__(self, data_path: Path = DATA_DIR / "graph_data.parquet"):
        self.df = pd.read_parquet(data_path)

    def replay(self, rule: Rule, days: int = 7) -> dict:
        """
        回放 rule。demo 里 days 参数只影响用于评估的样本量。
        为了 demo 效果,当 days 覆盖不到样本时,回退到全量。
        """
        df = self.df
        # 简化:按 timestamp 取最近 days 天,但若窗口过窄漏掉团伙则用全量
        if days > 0:
            tmax = df["timestamp"].max()
            windowed = df[df["timestamp"] >= tmax - days * 86400]
            # 若窗口内看不到欺诈样本,demo 里回退到全量
            if (windowed["true_label"] == "fraud").sum() == 0:
                pass  # 保留 df=全量
            else:
                df = windowed

        mask = pd.Series([True] * len(df), index=df.index)
        for c in rule.conditions:
            if c["type"] == "attribute":
                col = c["field"]
                if col not in df.columns:
                    continue
                val = c["value"]
                op = c["op"]
                if op == "==":
                    mask &= (df[col] == val)
                elif op == "<=":
                    mask &= (df[col] <= val)
                elif op == ">=":
                    mask &= (df[col] >= val)

        # shared_entity 用近似:如果规则要求 shared_device>=3,过滤出高共享度用户
        for c in rule.conditions:
            if c["type"] == "shared_entity":
                et = c["entity_type"]
                col = et if et in df.columns else None
                if col:
                    # 找出该实体被多少不同用户使用
                    entity_counts = df.groupby(col)["user_id"].nunique()
                    high_share_entities = entity_counts[entity_counts >= c["min_shared_users"]].index
                    mask &= df[col].isin(high_share_entities)

        hit = df[mask]
        total_fraud = int((df["true_label"] == "fraud").sum())
        total_normal = int((df["true_label"] == "normal").sum())
        tp = int((hit["true_label"] == "fraud").sum())
        fp = int((hit["true_label"] == "normal").sum())
        recall = tp / max(total_fraud, 1)
        fp_rate = fp / max(total_normal, 1)
        precision = tp / max(tp + fp, 1)

        return {
            "rule_id": rule.rule_id,
            "hits_total": int(len(hit)),
            "true_positives": tp,
            "false_positives": fp,
            "recall": recall,
            "fp_rate": fp_rate,
            "precision": precision,
            "hit_user_ids": hit["user_id"].tolist()[:20],
        }
