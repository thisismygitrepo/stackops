from typing import Literal, TypeAlias


PaneCategory: TypeAlias = Literal["idle", "running", "exited", "unknown"]
SummaryBackend: TypeAlias = Literal["tmux", "t", "herdr", "h", "aoe", "a", "tuios", "u", "auto"]
ResolvedSummaryBackend: TypeAlias = Literal["tmux", "herdr", "aoe", "tuios"]
