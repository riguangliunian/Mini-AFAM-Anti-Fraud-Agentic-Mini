"""模型刷新轨迹Memory和漂移事件检索。"""

import json
import math
from pathlib import Path

from .state import RefreshState, RefreshTrajectory


DATA_DIR = Path(__file__).parents[2] / "data" / "model_refresh"
DEFAULT_PATH = Path(__file__).parents[2] / "logs" / "refresh_memory.jsonl"


class RefreshMemory:
    def __init__(self, path: Path = DEFAULT_PATH, include_seed: bool = True,
                 index_writes: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.index_writes = index_writes
        self.items: list[dict] = []
        seed_path = DATA_DIR / "seed_refresh_trajectories.json"
        if include_seed and seed_path.exists():
            self.items.extend(json.loads(seed_path.read_text()).get("trajectories", []))
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.items.append(json.loads(line))

    def save(self, trajectory: RefreshTrajectory) -> None:
        item = trajectory.to_dict()
        with self.path.open("a") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        if self.index_writes:
            self.items.append(item)

    def retrievable(self) -> list[dict]:
        return [x for x in self.items if x.get("label") == "accepted" and x.get("refresh_success")]


class RefreshRetrieval:
    METRIC_KEYS = (
        "node_feature_psi", "edge_type_psi", "degree_shift", "embedding_mmd",
        "missing_rate_change", "label_maturity_drop",
    )

    def __init__(self, memory: RefreshMemory):
        self.memory = memory

    def search(self, state: RefreshState, top_k: int = 3) -> list[dict]:
        results = []
        for item in self.memory.retrievable():
            fp = item.get("drift_fingerprint", {})
            distance = math.sqrt(sum(
                (float(state.drift_signals.get(k, 0)) - float(fp.get(k, 0))) ** 2
                for k in self.METRIC_KEYS
            ))
            similarity = 1.0 / (1.0 + distance * 3.0)
            results.append({"trajectory": item, "similarity": similarity})
        return sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]
