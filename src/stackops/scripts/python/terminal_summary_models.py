from typing import Literal, TypeAlias


PaneCategory: TypeAlias = Literal["idle", "running", "exited", "unknown"]
SummaryBackend: TypeAlias = Literal["tmux", "t", "herdr", "h", "aoe", "e", "tuios", "u", "auto", "a"]
ResolvedSummaryBackend: TypeAlias = Literal["tmux", "herdr", "aoe", "tuios"]
