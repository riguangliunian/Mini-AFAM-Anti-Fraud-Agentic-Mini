"""
GraphMiner:图分析 → 自然语言诊断报告。

关键设计:
- Python 处理图,LLM 不直接读邻接结构
- 输出既有 JSON 指标,也有一段自然语言报告
- 报告是 Orchestrator 唯一的图输入,防止上下文爆炸
"""

import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class GraphMiner:
    """
    有状态的图分析器。加载全图一次,后续在子图上分析。
    """

    def __init__(self, graph_path: Path = DATA_DIR / "entity_graph.pkl"):
        with open(graph_path, "rb") as f:
            self.G: nx.MultiGraph = pickle.load(f)

    # ===== 图动作 =====

    def expand_neighbors(self, seeds: list[str], hop: int = 1,
                         edge_type: str | None = None) -> list[str]:
        """
        从种子扩展 K 度邻居,按边类型过滤。
        语义上 hop=1 = "1 度用户邻居"(即通过一个共享实体的其他用户),
        内部走 2 步图节点(user → entity → user)。
        """
        # 每个"用户 hop"对应图上的 2 步
        graph_steps = hop * 2
        frontier = set(seeds)
        visited = set(seeds)
        seed_set = set(seeds)
        for step in range(graph_steps):
            next_frontier = set()
            for node in frontier:
                if node not in self.G:
                    continue
                # 判断当前是"user → entity"还是"entity → user"
                cur_type = self.G.nodes[node].get("node_type")
                for nbr in self.G.neighbors(node):
                    if nbr in visited:
                        continue
                    nbr_type = self.G.nodes[nbr].get("node_type")
                    # 只按需要的方向走
                    if cur_type == "user" and nbr_type == "user":
                        continue  # 用户间无直接边
                    if edge_type and cur_type == "user":
                        edges = self.G.get_edge_data(node, nbr) or {}
                        matched = any(e.get("edge_type") == f"has_{edge_type}"
                                       or e.get("edge_type") == edge_type
                                       for e in edges.values())
                        if not matched:
                            continue
                    next_frontier.add(nbr)
                    visited.add(nbr)
            frontier = next_frontier
        # 只返回 user 节点
        return [n for n in visited if self.G.nodes[n].get("node_type") == "user"
                and n not in seed_set] + list(seeds)

    def shared_entity_stats(self, users: list[str]) -> dict[str, dict]:
        """统计给定 users 之间共享的实体。"""
        entity_users = defaultdict(set)  # entity -> set(user)
        for u in users:
            if u not in self.G:
                continue
            for nbr in self.G.neighbors(u):
                node_type = self.G.nodes[nbr].get("node_type")
                if node_type in ("device_id", "ip", "phone", "contact"):
                    entity_users[nbr].add(u)

        result = defaultdict(list)  # by entity_type
        for entity, sharers in entity_users.items():
            if len(sharers) >= 2:
                etype = self.G.nodes[entity].get("node_type")
                result[etype].append({
                    "entity": entity,
                    "shared_by": sorted(sharers),
                    "count": len(sharers),
                })
        # 排序:按共享数降序
        for k in result:
            result[k].sort(key=lambda x: x["count"], reverse=True)
        return dict(result)

    def find_community(self, users: list[str], min_size: int = 3) -> list[list[str]]:
        """
        用连通分量代替真正的社区发现(demo 简化)。
        真实项目应用 Louvain。
        """
        sub = self._user_projection(users)
        components = [list(c) for c in nx.connected_components(sub) if len(c) >= min_size]
        components.sort(key=len, reverse=True)
        return components

    def temporal_burst(self, users: list[str],
                       timestamps: dict[str, int],
                       window_hours: int = 4) -> dict:
        """检测集中申请。"""
        ts = sorted([timestamps[u] for u in users if u in timestamps])
        if len(ts) < 3:
            return {"burst_detected": False, "max_in_window": len(ts)}
        max_in_window = 0
        window_sec = window_hours * 3600
        j = 0
        for i in range(len(ts)):
            while j < len(ts) and ts[j] - ts[i] <= window_sec:
                j += 1
            max_in_window = max(max_in_window, j - i)
        return {
            "burst_detected": max_in_window >= max(3, len(ts) // 2),
            "max_in_window": max_in_window,
            "total": len(ts),
            "window_hours": window_hours,
        }

    def compute_metrics(self, users: list[str], df=None) -> dict[str, Any]:
        """算一堆风险指标。df 是原始特征表(见 generate_data 输出)。"""
        m = {"suspect_count": len(users)}
        if df is not None and len(users) > 0:
            sub = df[df["user_id"].isin(users)]
            m["new_account_ratio"] = float(sub["is_new_account"].mean()) if len(sub) else 0.0
            m["avg_account_age_days"] = float(sub["account_age_days"].mean()) if len(sub) else 0.0
            m["night_apply_ratio"] = float(sub["night_apply"].mean()) if len(sub) else 0.0
            m["avg_input_speed_ms"] = float(sub["input_speed_ms"].mean()) if len(sub) else 0.0
            m["paste_used_ratio"] = float(sub["paste_used"].mean()) if len(sub) else 0.0
            m["avg_label_maturity"] = float(sub["label_maturity"].mean()) if len(sub) else 0.5
        return m

    # ===== 主入口:分析 + 报告 =====

    def analyze(self, suspect_users: list[str], df=None) -> dict[str, Any]:
        """
        输入:可疑用户集合
        输出:{
            "report": 自然语言诊断报告(LLM 主读),
            "metrics": 数值指标,
            "shared_entities": {...},
            "communities": [...],
            "fingerprint": 结构指纹(供 Retrieval 用),
        }
        """
        shared = self.shared_entity_stats(suspect_users)
        communities = self.find_community(suspect_users)
        timestamps = {}
        if df is not None:
            ts_map = df.set_index("user_id")["timestamp"].to_dict()
            timestamps = {u: ts_map[u] for u in suspect_users if u in ts_map}
        burst = self.temporal_burst(suspect_users, timestamps)
        metrics = self.compute_metrics(suspect_users, df)

        # 生成自然语言报告
        lines = [f"Subgraph analysis of {len(suspect_users)} suspect users:"]
        # 共享实体摘要
        for etype, entries in shared.items():
            if entries:
                top = entries[0]
                lines.append(
                    f"- Shared {etype}: top '{top['entity']}' shared by "
                    f"{top['count']} users ({', '.join(top['shared_by'][:5])}"
                    f"{'...' if top['count']>5 else ''})"
                )
        # 社区
        if communities:
            lines.append(f"- Communities detected: {len(communities)}, largest size = {len(communities[0])}")
        else:
            lines.append("- No community structure detected (isolated or sparsely connected).")
        # 时间聚集
        if burst["burst_detected"]:
            lines.append(f"- Temporal burst: {burst['max_in_window']} applications within {burst['window_hours']}h window")
        # 风险指标
        if "new_account_ratio" in metrics:
            lines.append(f"- New account ratio: {metrics['new_account_ratio']:.0%}, "
                          f"night apply: {metrics['night_apply_ratio']:.0%}, "
                          f"paste used: {metrics['paste_used_ratio']:.0%}")
        if "avg_label_maturity" in metrics:
            lines.append(f"- Avg label maturity: {metrics['avg_label_maturity']:.2f} "
                          f"({'mature' if metrics['avg_label_maturity']>0.6 else 'IMMATURE'})")

        report = "\n".join(lines)

        fingerprint = {
            "size_bucket": self._bucket(len(suspect_users), [3, 8, 15]),
            "community_count_bucket": self._bucket(len(communities), [0, 1, 3]),
            "burst": burst["burst_detected"],
            # 用 list(sorted) 保持与 JSON 反序列化后的类型一致
            "shared_entity_types": sorted(shared.keys()),
            "new_account_high": metrics.get("new_account_ratio", 0) > 0.5,
        }

        return {
            "report": report,
            "metrics": metrics,
            "shared_entities": shared,
            "communities": communities,
            "burst": burst,
            "fingerprint": fingerprint,
        }

    # ===== 辅助 =====

    def _user_projection(self, users: list[str]) -> nx.Graph:
        """把 users 通过共享实体连成用户-用户图。"""
        g = nx.Graph()
        g.add_nodes_from(users)
        user_set = set(users)
        entity_users = defaultdict(list)
        for u in users:
            if u not in self.G:
                continue
            for nbr in self.G.neighbors(u):
                nt = self.G.nodes[nbr].get("node_type")
                if nt in ("device_id", "ip", "contact"):
                    entity_users[nbr].append(u)
        for entity, sharers in entity_users.items():
            for i in range(len(sharers)):
                for j in range(i + 1, len(sharers)):
                    g.add_edge(sharers[i], sharers[j])
        return g

    @staticmethod
    def _bucket(v, cutoffs) -> str:
        if v <= cutoffs[0]:
            return "small"
        if v <= cutoffs[1]:
            return "medium"
        if v <= cutoffs[2]:
            return "large"
        return "xlarge"
