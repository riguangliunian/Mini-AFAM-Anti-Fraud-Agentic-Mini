"""
Trajectory Memory:存储每次调查产生的完整轨迹。

对应 ACRM 论文的 Structured Memory(Section 3.1)。
简化点:用 JSON 文件持久化,不用向量数据库(demo 项目够用)。
"""

import json
from pathlib import Path
from typing import Optional

from .state import Trajectory


DEFAULT_MEMORY_PATH = Path(__file__).parent.parent / "logs" / "trajectory_memory.jsonl"
SEED_MEMORY_PATH = Path(__file__).parent.parent / "data" / "seed_trajectories.json"


class TrajectoryMemory:
    """
    简易 JSON-lines 轨迹存储。
    生产环境替换为向量数据库 + 图检索,demo 用文件即可。
    """

    def __init__(self, path: Path = DEFAULT_MEMORY_PATH,
                 include_seed: bool = True,
                 index_writes: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.trajectories: list[dict] = []
        self.index_writes = index_writes
        # 载入种子轨迹(手工准备的历史案例,用于 cold-start retrieval)
        if include_seed and SEED_MEMORY_PATH.exists():
            with open(SEED_MEMORY_PATH) as f:
                self.trajectories.extend(json.load(f).get("trajectories", []))
        # 载入本地历史
        if self.path.exists():
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.trajectories.append(json.loads(line))

    def save(self, traj: Trajectory) -> None:
        d = traj.to_dict()
        if self.index_writes:
            self.trajectories.append(d)
        with open(self.path, "a") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    def all(self) -> list[dict]:
        return list(self.trajectories)

    def retrievable(self) -> list[dict]:
        """只返回已审核通过且不存在工具失败的历史轨迹。"""
        result = []
        for traj in self.trajectories:
            if traj.get("label") != "accepted":
                continue
            outcomes = [s.get("outcome", {}) for s in traj.get("steps", [])]
            if outcomes and all(o.get("success", False) for o in outcomes):
                result.append(traj)
        return result

    def clear_local(self) -> None:
        """只清本地新增,不清 seed。"""
        if self.path.exists():
            self.path.unlink()
        self.trajectories = [t for t in self.trajectories if t.get("_source") == "seed"]
