from dataclasses import dataclass
from typing import Literal, TypeAlias


TraceUntil: TypeAlias = Literal["idle-shell", "all-exited", "exit-code", "session-missing"]
PaneCategory: TypeAlias = Literal["idle-shell", "running", "exited", "unknown"]


@dataclass(frozen=True, slots=True)
class TracePaneState:
    window_index: str
    window_name: str
    pane_index: str
    process_name: str
    status_text: str
    cwd: str
    is_active: bool
    category: PaneCategory
    exit_code: int | None
    matched: bool


@dataclass(frozen=True, slots=True)
class TraceSnapshot:
    session_name: str
    session_exists: bool
    total_windows: int
    panes: tuple[TracePaneState, ...]
    total_targets: int
    matched_targets: int
    pane_warning: str | None
    session_error: str | None
    criterion_satisfied: bool
    idle_shell_panes: int
    running_panes: int
    exited_panes: int
    unknown_panes: int


def pane_matches_criterion(
    category: PaneCategory,
    pane_exit_code: int | None,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> bool:
    match until:
        case "idle-shell":
            return category == "idle-shell"
        case "all-exited":
            return category == "exited"
        case "exit-code":
            return category == "exited" and pane_exit_code == expected_exit_code
        case "session-missing":
            return False


def build_missing_snapshot(
    session_name: str,
    until: TraceUntil,
    session_error: str | None,
) -> TraceSnapshot:
    matched_targets = 1 if until == "session-missing" else 0
    total_targets = 1 if until == "session-missing" else 0
    return TraceSnapshot(
        session_name=session_name,
        session_exists=False,
        total_windows=0,
        panes=(),
        total_targets=total_targets,
        matched_targets=matched_targets,
        pane_warning=None,
        session_error=session_error,
        criterion_satisfied=until == "session-missing",
        idle_shell_panes=0,
        running_panes=0,
        exited_panes=0,
        unknown_panes=0,
    )
