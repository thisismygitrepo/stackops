from dataclasses import dataclass
from typing import Literal, NewType


WorkspaceId = NewType("WorkspaceId", str)
TabId = NewType("TabId", str)
PaneId = NewType("PaneId", str)

type HerdrStatus = Literal["blocked", "done", "idle", "unknown", "working"]
type KeepReason = Literal[
    "recent",
    "active",
    "launch_successor",
    "tracker",
    "unmanaged",
    "incomplete_snapshot",
]
type CloseSkipReason = Literal["already_absent", "state_changed", "workspace_absent"]
type IterWorkspaceTrackPhase = Literal[
    "within_budget",
    "stop_requested",
    "draining",
    "ready_to_close",
    "closed",
    "failed",
]


@dataclass(frozen=True, slots=True)
class HerdrWorkspace:
    workspace_id: WorkspaceId
    label: str
    number: int
    active_tab_id: TabId
    agent_status: HerdrStatus
    focused: bool
    pane_count: int
    tab_count: int


@dataclass(frozen=True, slots=True)
class HerdrTab:
    tab_id: TabId
    workspace_id: WorkspaceId
    label: str
    number: int
    agent_status: HerdrStatus
    focused: bool
    pane_count: int


@dataclass(frozen=True, slots=True)
class HerdrAgent:
    agent: str
    agent_status: HerdrStatus
    workspace_id: WorkspaceId
    tab_id: TabId
    pane_id: PaneId
    cwd: str
    foreground_cwd: str
    focused: bool
    name: str | None


@dataclass(frozen=True, slots=True)
class HerdrPane:
    pane_id: PaneId
    workspace_id: WorkspaceId
    tab_id: TabId
    agent_status: HerdrStatus
    agent: str | None
    label: str | None


@dataclass(frozen=True, slots=True)
class HerdrSnapshot:
    workspaces: tuple[HerdrWorkspace, ...]
    tabs: tuple[HerdrTab, ...]
    panes: tuple[HerdrPane, ...]
    agents: tuple[HerdrAgent, ...]


@dataclass(frozen=True, slots=True)
class ProtectedTab:
    tab: HerdrTab
    reason: KeepReason


@dataclass(frozen=True, slots=True)
class IterWorkspaceClosePlan:
    workspace: HerdrWorkspace
    tabs: tuple[HerdrTab, ...]
    retained_tabs: tuple[HerdrTab, ...]
    protected_tabs: tuple[ProtectedTab, ...]
    closable_tabs: tuple[HerdrTab, ...]
    retain_previous: int

    def __post_init__(self) -> None:
        tab_ids = tuple(tab.tab_id for tab in self.tabs)
        categorized_ids = (
            *(tab.tab_id for tab in self.retained_tabs),
            *(protected.tab.tab_id for protected in self.protected_tabs),
            *(tab.tab_id for tab in self.closable_tabs),
        )
        if len(tab_ids) != len(set(tab_ids)):
            raise ValueError("Iter workspace close plan contains duplicate tabs.")
        if len(categorized_ids) != len(set(categorized_ids)):
            raise ValueError("Iter workspace close plan categories must be disjoint.")
        if set(categorized_ids) != set(tab_ids):
            raise ValueError("Iter workspace close plan categories must cover every tab.")


@dataclass(frozen=True, slots=True)
class SkippedTabClose:
    tab: HerdrTab
    reason: CloseSkipReason


@dataclass(frozen=True, slots=True)
class FailedTabClose:
    tab: HerdrTab
    message: str


@dataclass(frozen=True, slots=True)
class IterWorkspaceClose:
    workspace: HerdrWorkspace
    retained_tabs: tuple[HerdrTab, ...]
    protected_tabs: tuple[ProtectedTab, ...]
    closed_tabs: tuple[HerdrTab, ...]
    already_absent_tabs: tuple[HerdrTab, ...]
    skipped_tabs: tuple[SkippedTabClose, ...]
    failed_tabs: tuple[FailedTabClose, ...]

    def __post_init__(self) -> None:
        categorized_ids = (
            *(tab.tab_id for tab in self.retained_tabs),
            *(protected.tab.tab_id for protected in self.protected_tabs),
            *(tab.tab_id for tab in self.closed_tabs),
            *(tab.tab_id for tab in self.already_absent_tabs),
            *(skipped.tab.tab_id for skipped in self.skipped_tabs),
            *(failed.tab.tab_id for failed in self.failed_tabs),
        )
        if len(categorized_ids) != len(set(categorized_ids)):
            raise ValueError("Iter workspace close result categories must be disjoint.")


@dataclass(frozen=True, slots=True)
class IterWorkspaceStatus:
    workspace: HerdrWorkspace
    plan: IterWorkspaceClosePlan
    latest_iteration: int | None
    latest_agent: HerdrAgent | None
    latest_agent_tab: HerdrTab | None


@dataclass(frozen=True, slots=True)
class IterWorkspaceTrackResult:
    workspace_id: WorkspaceId
    workspace: HerdrWorkspace | None
    latest_iteration: int | None
    max_iterations: int
    phase: IterWorkspaceTrackPhase
    message: str | None


@dataclass(frozen=True, slots=True)
class IterWorkspaceTrackCheck:
    status: IterWorkspaceStatus | None
    track_result: IterWorkspaceTrackResult
    close_result: IterWorkspaceClose | None
