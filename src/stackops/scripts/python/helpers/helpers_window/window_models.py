from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


WindowAction = Literal["minimize", "maximize", "unminimize", "focus", "close"]


@dataclass(frozen=True)
class WindowEntry:
    app: str
    title: str
    minimized: bool
    apply_action: Callable[[WindowAction], None]
