from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend


type RankingMetric = Literal["distance", "score"]
type SemanticStage = Literal["options", "install", "discover", "index", "search", "parse"]


@dataclass(frozen=True, slots=True)
class SemanticHit:
    path: Path
    start_line: int
    end_line: int
    focus_line: int
    metric: RankingMetric
    value: float
    content: str


@dataclass(frozen=True, slots=True)
class SemanticSuccess:
    hits: list[SemanticHit]


@dataclass(frozen=True, slots=True)
class SemanticFailure:
    backend: SemanticBackend
    stage: SemanticStage
    message: str


type SemanticOutcome = SemanticSuccess | SemanticFailure
