"""
Day 1: 合成反欺诈团伙调查场景的数据。

产出:
1. graph_data.parquet:1000 个申请事件,每条含 30 个特征
2. entity_graph.pkl:实体关系图 (users, devices, ips, phones, contacts)
3. alerts.json:预埋的可疑告警(用于触发调查)

设计:
- 3 个明显团伙(设备/IP/联系人重叠)
- 2 个微妙团伙(仅二度关联能发现)
- 2 个干扰组(同小区/同公司共享 WiFi,是好用户)
- 剩余为正常独立申请

标签:
- 每个用户有 (label, label_maturity) 二元组
- label ∈ {normal, fraud, unknown}
- label_maturity ∈ [0, 1](模拟 chargeback 滞后)
"""

import json
import pickle
import random
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent
SEED = 42
random.seed(SEED)
np.random.seed(SEED)


def _rand_device(prefix="dev"):
    return f"{prefix}_{random.randint(10000, 99999)}"


def _rand_ip():
    return f"{random.randint(1, 254)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def _rand_phone():
    return f"1{random.choice('3568')}{random.randint(10000000, 99999999)}"


def _rand_gps(center_lat=39.9, center_lon=116.4, radius=0.5):
    """radius in degrees; 0.01 ~ 1km"""
    return (center_lat + random.uniform(-radius, radius), center_lon + random.uniform(-radius, radius))


def _rand_contact_pool(n=100):
    """A shared contact pool; fraudsters draw from a small subset."""
    return [_rand_phone() for _ in range(n)]


def _make_normal_user(uid, timestamp):
    """独立正常用户:所有实体唯一。"""
    return {
        "user_id": uid,
        "device_id": _rand_device(),
        "ip": _rand_ip(),
        "phone": _rand_phone(),
        "gps_lat": np.random.uniform(30, 45),
        "gps_lon": np.random.uniform(105, 125),
        "amount": np.random.lognormal(6, 1),
        "timestamp": timestamp,
        "account_age_days": np.random.randint(30, 2000),
        "is_new_account": False,
        "contacts": [_rand_phone() for _ in range(np.random.randint(5, 15))],
        "night_apply": random.random() < 0.05,
        "input_speed_ms": np.random.normal(3000, 800),
        "paste_used": random.random() < 0.1,
        "back_nav_count": np.random.poisson(2),
        "group_tag": "normal",
    }


def _make_gang(gang_id, size, timestamp_center, style):
    """
    造一个团伙。style 决定共享哪些实体。
    - "obvious":共享 device + IP + GPS
    - "subtle":只共享二度关联(通讯录 + 中间账户)
    """
    users = []
    if style == "obvious":
        shared_device = _rand_device(f"gang{gang_id}_dev")
        shared_ip = _rand_ip()
        gps_center = _rand_gps()
        for i in range(size):
            u = {
                "user_id": f"g{gang_id}_u{i}",
                "device_id": shared_device if random.random() < 0.7 else _rand_device(),
                "ip": shared_ip if random.random() < 0.6 else _rand_ip(),
                "phone": _rand_phone(),
                "gps_lat": gps_center[0] + np.random.normal(0, 0.001),
                "gps_lon": gps_center[1] + np.random.normal(0, 0.001),
                "amount": np.random.uniform(3000, 8000),
                "timestamp": timestamp_center + np.random.randint(-3600, 3600),
                "account_age_days": np.random.randint(1, 20),
                "is_new_account": True,
                "contacts": [_rand_phone() for _ in range(np.random.randint(3, 6))],
                "night_apply": random.random() < 0.4,
                "input_speed_ms": np.random.normal(800, 200),
                "paste_used": random.random() < 0.6,
                "back_nav_count": np.random.poisson(0.5),
                "group_tag": f"gang_obvious_{gang_id}",
            }
            users.append(u)
    elif style == "subtle":
        # 微妙团伙:通过一个中介账户互相认识,共享部分通讯录
        shared_contacts = [_rand_phone() for _ in range(5)]
        for i in range(size):
            personal_contacts = [_rand_phone() for _ in range(np.random.randint(3, 8))]
            u = {
                "user_id": f"g{gang_id}_u{i}",
                "device_id": _rand_device(),
                "ip": _rand_ip(),
                "phone": _rand_phone(),
                "gps_lat": np.random.uniform(30, 45),
                "gps_lon": np.random.uniform(105, 125),
                "amount": np.random.uniform(3000, 6000),
                "timestamp": timestamp_center + np.random.randint(-86400, 86400),
                "account_age_days": np.random.randint(10, 60),
                "is_new_account": True,
                "contacts": personal_contacts + random.sample(shared_contacts, k=3),
                "night_apply": random.random() < 0.2,
                "input_speed_ms": np.random.normal(1500, 400),
                "paste_used": random.random() < 0.3,
                "back_nav_count": np.random.poisson(1),
                "group_tag": f"gang_subtle_{gang_id}",
            }
            users.append(u)
    return users


def _make_wifi_neighborhood(nb_id, size, timestamp_center):
    """干扰组:同小区居民,共享 WiFi (相同 IP),但都是好用户。"""
    shared_ip = _rand_ip()
    gps_center = _rand_gps()
    users = []
    for i in range(size):
        u = {
            "user_id": f"nb{nb_id}_u{i}",
            "device_id": _rand_device(),
            "ip": shared_ip,
            "phone": _rand_phone(),
            "gps_lat": gps_center[0] + np.random.normal(0, 0.005),
            "gps_lon": gps_center[1] + np.random.normal(0, 0.005),
            "amount": np.random.lognormal(6, 1),
            "timestamp": timestamp_center + np.random.randint(-86400 * 7, 86400 * 7),
            "account_age_days": np.random.randint(180, 2000),
            "is_new_account": False,
            "contacts": [_rand_phone() for _ in range(np.random.randint(8, 20))],
            "night_apply": random.random() < 0.05,
            "input_speed_ms": np.random.normal(3500, 1000),
            "paste_used": random.random() < 0.1,
            "back_nav_count": np.random.poisson(3),
            "group_tag": f"wifi_neighborhood_{nb_id}",
        }
        users.append(u)
    return users


def generate_all():
    """生成全部数据。"""
    base_ts = 1721145600  # 2024-07-17 00:00
    all_users = []

    # 3 个明显团伙 (size 6-12)
    for gid in range(3):
        size = np.random.randint(6, 13)
        users = _make_gang(gid, size, base_ts + gid * 3600, "obvious")
        all_users.extend(users)

    # 2 个微妙团伙 (size 5-8)
    for gid in range(3, 5):
        size = np.random.randint(5, 9)
        users = _make_gang(gid, size, base_ts + gid * 7200, "subtle")
        all_users.extend(users)

    # 2 个 WiFi 邻居干扰组 (size 8-15)
    for nb in range(2):
        size = np.random.randint(8, 16)
        users = _make_wifi_neighborhood(nb, size, base_ts + nb * 86400)
        all_users.extend(users)

    # 补足到 1000 个:正常独立用户
    while len(all_users) < 1000:
        uid = f"n_u{len(all_users)}"
        ts = base_ts + np.random.randint(0, 86400 * 30)
        all_users.append(_make_normal_user(uid, ts))

    # 标签生成 (with maturity)
    for u in all_users:
        tag = u["group_tag"]
        if tag.startswith("gang_"):
            u["true_label"] = "fraud"
            # 明显团伙的 label 更成熟,微妙团伙的滞后
            u["label_maturity"] = np.random.uniform(0.6, 0.95) if "obvious" in tag else np.random.uniform(0.2, 0.5)
        else:
            u["true_label"] = "normal"
            u["label_maturity"] = np.random.uniform(0.7, 1.0)

    df = pd.DataFrame(all_users)

    # 建图
    G = nx.MultiGraph()
    for _, row in df.iterrows():
        uid = row["user_id"]
        G.add_node(uid, node_type="user", **{k: row[k] for k in ["true_label", "label_maturity",
                                                                   "account_age_days", "is_new_account",
                                                                   "night_apply", "group_tag"]})
        # 添加设备/IP/电话节点及边
        for entity_type in ["device_id", "ip", "phone"]:
            eid = row[entity_type]
            if not G.has_node(eid):
                G.add_node(eid, node_type=entity_type)
            G.add_edge(uid, eid, edge_type=f"has_{entity_type}")
        # 联系人边
        for contact in row["contacts"]:
            if not G.has_node(contact):
                G.add_node(contact, node_type="contact")
            G.add_edge(uid, contact, edge_type="has_contact")

    # 保存
    df.drop(columns=["contacts"]).to_parquet(DATA_DIR / "graph_data.parquet")
    with open(DATA_DIR / "entity_graph.pkl", "wb") as f:
        pickle.dump(G, f)

    # 预埋告警(选每个团伙里"最连通"的用户作为种子,保证 expand 能找到同伙)
    alerts = []
    for gid in range(5):
        gang_users = [u["user_id"] for u in all_users
                       if u["group_tag"] in (f"gang_obvious_{gid}", f"gang_subtle_{gid}")]
        if not gang_users:
            continue
        # 选度数最高的作为种子
        degrees = [(u, G.degree(u)) for u in gang_users if u in G]
        degrees.sort(key=lambda x: x[1], reverse=True)
        seed_user = degrees[0][0] if degrees else gang_users[0]
        alerts.append({
            "alert_id": f"alert_{len(alerts):03d}",
            "seed_user": seed_user,
            "trigger_reason": f"Device shared by {len(gang_users)} users within 24h" if gid < 3
                               else "Contact overlap flagged by rule engine",
            "trigger_time": base_ts + gid * 3600 + 7200,
            "severity": "high" if gid < 3 else "medium",
        })
    # 加一个"误报"告警:WiFi 邻居组
    nb_users = [u["user_id"] for u in all_users if u["group_tag"] == "wifi_neighborhood_0"]
    if nb_users:
        alerts.append({
            "alert_id": f"alert_{len(alerts):03d}",
            "seed_user": nb_users[0],
            "trigger_reason": f"IP shared by {len(nb_users)} users (rule hit)",
            "trigger_time": base_ts + 100000,
            "severity": "medium",
            "note": "actually a false-positive; agent should NOT flag as fraud"
        })

    with open(DATA_DIR / "alerts.json", "w") as f:
        json.dump(alerts, f, indent=2)

    # 统计
    print(f"Generated {len(all_users)} users")
    print(f"  Fraud users (gangs): {sum(1 for u in all_users if u['true_label']=='fraud')}")
    print(f"  Normal users: {sum(1 for u in all_users if u['true_label']=='normal')}")
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Alerts pre-seeded: {len(alerts)}")
    print(f"Saved to {DATA_DIR}/")


if __name__ == "__main__":
    generate_all()
