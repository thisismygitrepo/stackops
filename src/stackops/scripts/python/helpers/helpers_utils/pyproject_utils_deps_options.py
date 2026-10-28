from typing import Literal, TypeAlias

DependencyBackend: TypeAlias = Literal["pyan", "pydeps"]
DependencyOutput: TypeAlias = Literal["json", "jsonic", "html"]
DependencyRankDirection: TypeAlias = Literal["TB", "BT", "LR", "RL"]
DependencyEdgeFilter: TypeAlias = Literal["all", "cycles", "dual"]
