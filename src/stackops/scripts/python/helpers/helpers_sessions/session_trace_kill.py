from dataclasses import dataclass
from subprocess import TimeoutExpired
from typing import Literal

from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command
from stackops.scripts.python.helpers.helpers_sessions.kill_impl import KilledTarget
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    TraceBackend,
    TracePaneState,
    TraceSnapshot,
)


type TraceKillAction = Literal["session", "window", "pane"]


@dataclass(frozen=True, slots=True)
class TraceKillCommand:
    argv: tuple[str, ...]
    summary: KilledTarget


@dataclass(frozen=True, slots=True)
class TraceKillPlan:
    commands: tuple[TraceKillCommand, ...]
    completed_session_names: frozenset[str]


def _build_trace_kill_command(
    backend: TraceBackend,
    action: TraceKillAction,
    target: str,
    session_name: str,
    window_name: str,
    detail: str,
) -> TraceKillCommand:
    if target.strip() in {"", "?"}:
        raise ValueError(f"Cannot kill {backend} {action} without a canonical target identifier.")

    match backend, action:
        case "tmux", "session":
            argv = ("tmux", "kill-session", "-t", target)
        case "tmux", "window":
            argv = ("tmux", "kill-window", "-t", target)
        case "tmux", "pane":
            argv = ("tmux", "kill-pane", "-t", target)
        case "herdr", "session":
            argv = ("herdr", "workspace", "close", target)
        case "herdr", "window":
            argv = ("herdr", "tab", "close", target)
        case "herdr", "pane":
            argv = ("herdr", "pane", "close", target)
        case "aoe", "session":
            argv = ("aoe", "session", "stop", target)
        case "aoe", "window" | "pane":
            raise ValueError("AoE only supports session-level trace cleanup.")

    summary = KilledTarget(
        action=action,
        session=session_name,
        window=window_name,
        detail=detail,
    )
    return TraceKillCommand(argv=argv, summary=summary)


def build_trace_kill_plan(
    backend: TraceBackend,
    snapshots: tuple[TraceSnapshot, ...],
) -> TraceKillPlan:
    commands: list[TraceKillCommand] = []
    completed_session_names: set[str] = set()

    for snapshot in snapshots:
        if snapshot.criterion_satisfied:
            completed_session_names.add(snapshot.session_name)
            if snapshot.session_exists:
                commands.append(
                    _build_trace_kill_command(
                        backend=backend,
                        action="session",
                        target=snapshot.session_target,
                        session_name=snapshot.session_name,
                        window_name="-",
                        detail=f"{len(snapshot.panes)} pane(s)",
                    )
                )
            continue

        if backend == "aoe":
            continue

        panes_by_window_target: dict[str, list[TracePaneState]] = {}
        for pane in snapshot.panes:
            panes_by_window_target.setdefault(pane.window_target, []).append(pane)

        for window_panes in panes_by_window_target.values():
            matched_panes = [pane for pane in window_panes if pane.matched]
            if len(matched_panes) == 0:
                continue
            if len(matched_panes) == len(window_panes):
                first_pane = window_panes[0]
                commands.append(
                    _build_trace_kill_command(
                        backend=backend,
                        action="window",
                        target=first_pane.window_target,
                        session_name=snapshot.session_name,
                        window_name=first_pane.window_name,
                        detail=f"{len(window_panes)} pane(s)",
                    )
                )
                continue
            for pane in matched_panes:
                commands.append(
                    _build_trace_kill_command(
                        backend=backend,
                        action="pane",
                        target=pane.pane_target,
                        session_name=snapshot.session_name,
                        window_name=pane.window_name,
                        detail=pane.process_name,
                    )
                )

    return TraceKillPlan(
        commands=tuple(commands),
        completed_session_names=frozenset(completed_session_names),
    )


def execute_trace_kill_plan(plan: TraceKillPlan) -> None:
    for command in plan.commands:
        try:
            result = run_command(list(command.argv), timeout=30.0)
        except (OSError, TimeoutExpired) as error:
            raise RuntimeError(f"Trace cleanup command failed: {' '.join(command.argv)}: {error}") from error
        if result.returncode == 0:
            continue
        detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
        raise RuntimeError(f"Trace cleanup command failed: {' '.join(command.argv)}: {detail}")
