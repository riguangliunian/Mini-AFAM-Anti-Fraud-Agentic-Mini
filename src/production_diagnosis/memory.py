"""Trajectory memory and retrieval for production diagnosis."""

import json
import math
from pathlib import Path

from .state import DiagnosisState, DiagnosisTrajectory


ROOT = Path(__file__).parents[2]
DATA_DIR = ROOT / "data" / "production_diagnosis"
DEFAULT_PATH = ROOT / "logs" / "diagnosis_memory.jsonl"


class DiagnosisMemory:
    def __init__(self, path: Path = DEFAULT_PATH, include_seed: bool = True,
                 index_writes: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.index_writes = index_writes
        self.items: list[dict] = []
        seed_path = DATA_DIR / "seed_diagnosis_trajectories.json"
        if include_seed and seed_path.exists():
            self.items.extend(json.loads(seed_path.read_text()).get("trajectories", []))
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.items.append(json.loads(line))

    def save(self, trajectory: DiagnosisTrajectory) -> None:
        item = trajectory.to_dict()
        with self.path.open("a") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        if self.index_writes:
            self.items.append(item)

    def retrievable(self) -> list[dict]:
        return [item for item in self.items if item.get("label") == "accepted" and item.get("success")]


class DiagnosisRetrieval:
    FINGERPRINT_KEYS = (
        "missing_rate_spike",
        "psi_max",
        "shap_shift",
        "behavior_shift",
        "graph_shift",
        "rule_hit_delta",
        "calibration_shift",
        "label_maturity_gap",
    )

    def __init__(self, memory: DiagnosisMemory):
        self.memory = memory

    def search(self, state: DiagnosisState, top_k: int = 3) -> list[dict]:
        query = self._fingerprint_from_state(state)
        scored = []
        for item in self.memory.retrievable():
            fp = item.get("diagnosis_fingerprint", {})
            distance = math.sqrt(sum(
                (float(query.get(k, 0.0)) - float(fp.get(k, 0.0))) ** 2
                for k in self.FINGERPRINT_KEYS
            ))
            similarity = 1.0 / (1.0 + 3.0 * distance)
            scored.append({"trajectory": item, "similarity": similarity})
        return sorted(scored, key=lambda x: x["similarity"], reverse=True)[:top_k]

    @classmethod
    def _fingerprint_from_state(cls, state: DiagnosisState) -> dict:
        alert = state.monitor_alert
        return {k: float(alert.get(k, 0.0)) for k in cls.FINGERPRINT_KEYS}
