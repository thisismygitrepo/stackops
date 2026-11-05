from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from typing import Literal, assert_never, cast

from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer


def _select_entries[T](entries: list[T], session: str | None, aliases: Callable[[T], tuple[str, ...]]) -> list[T]:
    if session is None:
        return entries
    matches = [entry for entry in entries if session in aliases(entry)]
    if not matches:
        raise ValueError(f"""Session or workspace '{session}' not found.""")
    if len(matches) > 1:
        raise ValueError(f"""Session or workspace '{session}' is ambiguous; pass its unique ID.""")
    return matches


def _herdr_entries(kind: Literal["workspaces", "tabs", "panes"], workspace_id: str | None) -> list[dict[str, object]]:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    command = ["herdr", kind.removesuffix("s"), "list"]
    if workspace_id is not None:
        command.extend(["--workspace", workspace_id])
    payload = _herdr_backend.run_json_command(command)
    result: object = payload.get("result") if payload is not None else None
    if not isinstance(result, dict):
        raise ValueError(f"""Unable to read Herdr {kind}.""")
    entries: object = result.get(kind)
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError(f"""Herdr returned invalid {kind}.""")
    return cast(list[dict[str, object]], entries)


def collect_summary(backend: SessionMultiplexer, session: str | None, show_tabs: bool) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    record: dict[str, object]
    include_details = show_tabs or session is not None
    match backend:
        case "tmux" | "zellij":
            if backend == "tmux":
                from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command
                from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import load_trace_snapshot

                result = run_command(["tmux", "list-sessions", "-F", "#S"])
                if result.returncode != 0:
                    detail = result.stderr.strip() or result.stdout.strip()
                    missing_socket = "error connecting to" in detail and "No such file or directory" in detail
                    if "no server running" not in detail and "no sessions" not in detail and not missing_socket:
                        raise ValueError(f"""Unable to list tmux sessions: {detail}""")
                    names: list[str] = []
                else:
                    names = [name for name in result.stdout.splitlines() if name]
            else:
                from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_session_names
                from stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij import load_trace_snapshot

                names = list_session_names()
            for name in _select_entries(entries=names, session=session, aliases=lambda name: (name,)):
                snapshot = load_trace_snapshot(session_name=name, until="idle-shell", expected_exit_code=None)
                if snapshot.session_error or snapshot.pane_warning or not snapshot.session_exists:
                    raise ValueError(snapshot.session_error or snapshot.pane_warning or f"""Session '{name}' disappeared.""")
                record = {
                    "name": name,
                    "id": snapshot.session_target,
                    "tab_count": snapshot.total_windows,
                    "pane_count": len(snapshot.panes),
                    "idle": snapshot.idle_shell_panes,
                    "running": snapshot.running_panes,
                    "exited": snapshot.exited_panes,
                    "unknown": snapshot.unknown_panes,
                }
                if include_details:
                    record["panes"] = [
                        {key: value for key, value in asdict(pane).items() if key != "matched"}
                        for pane in snapshot.panes
                    ]
                records.append(record)
        case "tuios":
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_idle import window_is_idle
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_session_entries, list_window_entries

            tuios_sessions = [entry for entry in list_session_entries() if not entry.saved]
            for entry in _select_entries(entries=tuios_sessions, session=session, aliases=lambda entry: (entry.name, entry.id)):
                windows = list_window_entries(session_name=entry.name)
                idle_states = [window_is_idle(window=window) for window in windows]
                record = {
                    "name": entry.name,
                    "id": entry.id,
                    "attached": entry.attached,
                    "last_active": entry.last_active,
                    "workspace_count": len({window.workspace for window in windows}),
                    "window_count": len(windows),
                    "idle": sum(idle is True for idle in idle_states),
                    "running": sum(idle is False for idle in idle_states),
                    "unknown": sum(idle is None for idle in idle_states),
                    "agent_states": dict(Counter(window.agent_state for window in windows if window.agent_state != "none")),
                }
                if include_details:
                    record["windows"] = [asdict(window) for window in windows]
                records.append(record)
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend
            from stackops.scripts.python.terminal_summary import herdr_workspace_display_name, herdr_workspace_id

            workspaces = _herdr_entries(kind="workspaces", workspace_id=None)
            selected_workspaces = _select_entries(
                entries=workspaces,
                session=session,
                aliases=lambda workspace: (herdr_workspace_display_name(workspace) or "", herdr_workspace_id(workspace) or ""),
            )
            for workspace in selected_workspaces:
                workspace_id = herdr_workspace_id(workspace)
                if workspace_id is None:
                    raise ValueError("Herdr returned a workspace without an ID.")
                tabs = _herdr_entries(kind="tabs", workspace_id=workspace_id)
                panes = _herdr_entries(kind="panes", workspace_id=workspace_id)
                agent_states = Counter(
                    state for entry in [workspace, *tabs, *panes]
                    if (state := _herdr_backend.entry_text(entry, "agent_status")) is not None
                )
                record = {
                    "name": herdr_workspace_display_name(workspace),
                    "id": workspace_id,
                    "focused": bool(workspace.get("focused")),
                    "tab_count": len(tabs),
                    "pane_count": len(panes),
                    "agent_count": sum(_herdr_backend.entry_text(pane, "agent") is not None for pane in panes),
                    "focused_tabs": sum(bool(tab.get("focused")) for tab in tabs),
                    "focused_panes": sum(bool(pane.get("focused")) for pane in panes),
                    "agent_states": dict(agent_states),
                    "cwd_counts": dict(Counter(
                        cwd for pane in panes
                        if (cwd := _herdr_backend.entry_text(pane, "foreground_cwd") or _herdr_backend.entry_text(pane, "cwd")) is not None
                    )),
                }
                if include_details:
                    record["tabs"] = tabs
                    record["panes"] = panes
                records.append(record)
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend
            from stackops.scripts.python.terminal_summary import aoe_session_entries_or_exit, collect_aoe_summary

            if show_tabs:
                raise ValueError("--tabs is only supported by tmux, Herdr, TUIOS, and Zellij; AoE sessions are already listed individually.")
            aoe_sessions = aoe_session_entries_or_exit()
            selected_sessions = _select_entries(
                entries=aoe_sessions,
                session=session,
                aliases=lambda entry: (_aoe_backend.session_title(entry) or "", _aoe_backend.session_id(entry) or ""),
            )
            for aoe_session in selected_sessions:
                aoe_summary = collect_aoe_summary(session=aoe_session)
                record = asdict(aoe_summary)
                record["id"] = aoe_summary.session_id
                records.append(record)
        case _:
            assert_never(backend)
    return records
