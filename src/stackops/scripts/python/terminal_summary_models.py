from typing import Literal, TypeAlias


PaneCategory: TypeAlias = Literal["idle", "running", "exited", "unknown"]
SummaryBackend: TypeAlias = Literal["tmux", "t", "herdr", "h", "aoe", "a", "tuios", "u", "auto"]
ResolvedSummaryBackend: TypeAlias = Literal["tmux", "herdr", "aoe", "tuios"]
SummarizeVocabulary: TypeAlias = Literal["layout", "l", "herdr", "h"]
LegacySummarizeBackend: TypeAlias = Literal["tmux", "t", "herdr", "h", "tuios", "u", "auto", "a"]
ResolvedSummarizeVocabulary: TypeAlias = Literal["layout", "herdr"]
