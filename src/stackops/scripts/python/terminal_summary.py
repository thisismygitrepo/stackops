"""Print running terminal session summaries."""

from collections import Counter
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypeAlias

import typer


PaneCategory: TypeAlias = Literal["idle", "running", "exited", "unknown"]
SummaryBackend: TypeAlias = Literal["tmux", "t", "herdr", "h", "aoe", "a", "auto"]
ResolvedSummaryBackend: TypeAlias = Literal["tmux", "herdr", "aoe"]


@dataclass(frozen=True)
class SessionSummary:
    name: str
    windows: int
    panes: int
    processes: int
    idle_shells: int
    running: int
    exited: int
    unknown: int
    idle_panes: str
    process_names: str


@dataclass(frozen=True)
class HerdrWorkspaceSummary:
    name: str
    workspace_id: str
    focused: bool
    tabs: int
    panes: int
    agents: int
    focused_tabs: int
    focused_panes: int
    agent_statuses: str
    cwd: str


@dataclass(frozen=True)
class AoeSessionSummary:
    name: str
    session_id: str
    status: str
    group: str
    agent: str
    path: str


JsonObject: TypeAlias = dict[str, Any]


def _pane_category(status: str) -> PaneCategory:
    if status == "idle shell":
        return "idle"
    if status.startswith("running:"):
        return "running"
    if status.startswith("exited ("):
        return "exited"
    return "unknown"


def _process_group_name(process_name: str) -> str:
    text = process_name.strip().strip("`")
    if text == "" or text == "—":
        return "—"
    return text.split(maxsplit=1)[0]


def _format_process_names(process_counts: Counter[str]) -> str:
    if not process_counts:
        return "—"
    rows = sorted(process_counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name} x{count}" if count > 1 else name for name, count in rows)


def _resolve_summary_backend(backend: SummaryBackend) -> ResolvedSummaryBackend:
    match backend:
        case "tmux" | "t" | "auto":
            return "tmux"
        case "herdr" | "h":
            return "herdr"
        case "aoe" | "a":
            return "aoe"


def _format_counts(counts: Counter[str]) -> str:
    if not counts:
        return "-"
    rows = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name} x{count}" if count > 1 else name for name, count in rows)


def _aoe_session_entries_or_exit() -> list[JsonObject]:
    from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend

    sessions = _aoe_backend.list_session_entries()
    if sessions is None:
        typer.echo(
            "Error: Unable to list AoE sessions. Confirm `aoe list --json` works.",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    return sessions


def _collect_aoe_summary(session: JsonObject) -> AoeSessionSummary:
    from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend

    return AoeSessionSummary(
        name=_aoe_backend.session_title(session) or _aoe_backend.session_id(session) or "-",
        session_id=_aoe_backend.session_id(session) or "-",
        status=_aoe_backend.session_status(session) or "-",
        group=_aoe_backend.entry_text(session, "group", "group_path", "groupPath") or "-",
        agent=_aoe_backend.entry_text(session, "agent", "tool", "command") or "-",
        path=_aoe_backend.entry_text(session, "path", "project_path", "projectPath", "workspace", "cwd") or "-",
    )


def _print_aoe_summary() -> None:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    sessions = _aoe_session_entries_or_exit()
    table = Table(
        title=f"AoE sessions ({len(sessions)})",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Session", style="bold cyan")
    table.add_column("ID")
    table.add_column("Status", style="green")
    table.add_column("Group", overflow="fold")
    table.add_column("Agent")
    table.add_column("Path", overflow="fold")

    for session in [_collect_aoe_summary(session=session) for session in sessions]:
        table.add_row(
            session.name,
            session.session_id,
            session.status,
            session.group,
            session.agent,
            session.path,
        )
    Console().print(table)


def _aoe_session_detail_markdown(session: JsonObject) -> str:
    summary = _collect_aoe_summary(session)
    return "\n".join(
        [
            f"# AoE Session: {summary.name}",
            "",
            "**backend:** aoe",
            f"**id:** {summary.session_id}",
            f"**status:** {summary.status}",
            f"**group:** {summary.group}",
            f"**agent:** {summary.agent}",
            f"**path:** {summary.path}",
        ]
    )


def _find_aoe_session(sessions: list[JsonObject], name: str) -> JsonObject | None:
    from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend

    for session in sessions:
        candidates = {
            _aoe_backend.session_title(session),
            _aoe_backend.session_id(session),
            _aoe_backend.session_identifier(session),
            _aoe_backend.session_display_name(session),
        }
        if name in candidates:
            return session
    return None


def _available_aoe_session_names(sessions: list[JsonObject]) -> list[str]:
    from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend

    names: list[str] = []
    for session in sessions:
        name = _aoe_backend.session_identifier(session)
        if name is not None:
            names.append(name)
    return names


def _resolve_aoe_session_name(session_name: str | None, choose_session: bool) -> str | None:
    from stackops.scripts.python.helpers.helpers_sessions._attach_common import interactive_choose_with_preview
    from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend

    if session_name is not None and choose_session:
        typer.echo("Error: --session cannot be used together with --choose-session.", err=True, color=True)
        raise typer.Exit(code=1)

    sessions = _aoe_session_entries_or_exit()
    if choose_session:
        option_to_identifier: dict[str, str] = {}
        options_to_preview_mapping: dict[str, str] = {}
        seen_labels: dict[str, int] = {}
        for session in sessions:
            identifier = _aoe_backend.session_identifier(session)
            if identifier is None:
                continue
            label = _aoe_backend.session_display_name(session)
            seen = seen_labels.get(label, 0)
            seen_labels[label] = seen + 1
            if seen:
                label = f"{label} ({_aoe_backend.session_id(session) or seen + 1})"
            option_to_identifier[label] = identifier
            options_to_preview_mapping[label] = _aoe_session_detail_markdown(session)

        if len(options_to_preview_mapping) == 0:
            typer.echo("Error: No AoE sessions are available.", err=True, color=True)
            raise typer.Exit(code=1)

        selection = interactive_choose_with_preview(
            msg="Choose an AoE session to summarize:",
            options_to_preview_mapping=options_to_preview_mapping,
        )
        if selection is None:
            typer.echo("Error: No AoE session selected.", err=True, color=True)
            raise typer.Exit(code=1)
        if isinstance(selection, list):
            selection = selection[0] if selection else None
        if selection not in option_to_identifier:
            typer.echo(f"Error: Unknown AoE session selected: {selection}", err=True, color=True)
            raise typer.Exit(code=1)
        return option_to_identifier[selection]

    if session_name is None:
        return None

    if _find_aoe_session(sessions, session_name) is None:
        available_names = _available_aoe_session_names(sessions)
        available = ", ".join(available_names) if available_names else "none"
        typer.echo(
            f"Error: AoE session '{session_name}' not found. Available sessions: {available}",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    return session_name


def _print_aoe_session_details(session_name: str) -> None:
    from rich.console import Console
    from rich.markdown import Markdown

    sessions = _aoe_session_entries_or_exit()
    session = _find_aoe_session(sessions, session_name)
    if session is None:
        available_names = _available_aoe_session_names(sessions)
        available = ", ".join(available_names) if available_names else "none"
        typer.echo(
            f"Error: AoE session '{session_name}' not found. Available sessions: {available}",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    Console().print(Markdown(_aoe_session_detail_markdown(session)))


def _collect_tmux_summary(session_name: str) -> SessionSummary:
    from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import classify_pane_status
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import collect_session_snapshot

    windows, panes_by_window, pane_warning = collect_session_snapshot(
        session_name=session_name,
        run_command_fn=run_command,
    )
    if windows is None:
        return SessionSummary(
            name=session_name,
            windows=0,
            panes=0,
            processes=0,
            idle_shells=0,
            running=0,
            exited=0,
            unknown=1,
            idle_panes="—",
            process_names=pane_warning or "unavailable",
        )

    category_counts: Counter[PaneCategory] = Counter()
    process_counts: Counter[str] = Counter()
    idle_panes: list[str] = []
    panes = 0
    for window in windows:
        for pane in panes_by_window.get(window["window_index"], []):
            process_name, status = classify_pane_status(pane=pane)
            category = _pane_category(status=status)
            category_counts[category] += 1
            panes += 1
            if category == "idle":
                idle_panes.append(f"{window['window_index']}.{pane['pane_index']}")
            if category == "running":
                process_counts[_process_group_name(process_name=process_name)] += 1

    return SessionSummary(
        name=session_name,
        windows=len(windows),
        panes=panes,
        processes=sum(process_counts.values()),
        idle_shells=category_counts["idle"],
        running=category_counts["running"],
        exited=category_counts["exited"],
        unknown=category_counts["unknown"],
        idle_panes=", ".join(idle_panes) if idle_panes else "—",
        process_names=_format_process_names(process_counts=process_counts),
    )


def _print_tmux_summary() -> None:
    from rich import box
    from rich.console import Console
    from rich.table import Table
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names

    console = Console()
    session_names = list_session_names()
    table = Table(
        title=f"tmux sessions ({len(session_names)})",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Session", style="bold cyan")
    table.add_column("Win", justify="right")
    table.add_column("Panes", justify="right")
    table.add_column("Proc", justify="right", style="green")
    table.add_column("Idle", justify="right", style="yellow")
    table.add_column("Run", justify="right", style="green")
    table.add_column("Exit", justify="right", style="red")
    table.add_column("Unk", justify="right", style="magenta")
    table.add_column("Idle Panes", overflow="fold")
    table.add_column("Process Names", overflow="fold")

    for session in [_collect_tmux_summary(session_name=name) for name in session_names]:
        table.add_row(
            session.name,
            str(session.windows),
            str(session.panes),
            str(session.processes),
            str(session.idle_shells),
            str(session.running),
            str(session.exited),
            str(session.unknown),
            session.idle_panes,
            session.process_names,
        )
    console.print(table)


def _print_tmux_session_details(session_name: str) -> None:
    from rich.console import Console
    from rich.markdown import Markdown
    from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import classify_pane_status
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import build_preview

    preview = build_preview(
        session_name=session_name,
        run_command_fn=run_command,
        classify_pane_status_fn=classify_pane_status,
    )
    Console().print(Markdown(preview))


def _herdr_workspace_entries_or_exit() -> list[JsonObject]:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    workspaces = _herdr_backend.list_workspace_entries()
    if workspaces is None:
        typer.echo(
            "Error: Unable to list Herdr workspaces. Confirm `herdr workspace list` works.",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    return workspaces


def _herdr_workspace_id(workspace: JsonObject) -> str | None:
    return _herdr_entry_text(workspace, "workspace_id")


def _herdr_workspace_display_name(workspace: JsonObject) -> str | None:
    label = _herdr_entry_text(workspace, "label")
    if label is not None:
        return label
    return _herdr_workspace_id(workspace)


def _herdr_entry_text(entry: JsonObject, key: str) -> str | None:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    return _herdr_backend.entry_text(entry, key)


def _collect_herdr_summary(workspace: JsonObject) -> HerdrWorkspaceSummary:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    name = _herdr_workspace_display_name(workspace) or "-"
    workspace_id = _herdr_workspace_id(workspace) or "-"
    tabs: list[JsonObject] = []
    panes: list[JsonObject] = []
    if workspace_id != "-":
        tabs = _herdr_backend.list_workspace_tab_entries(workspace_id)
        panes = _herdr_backend.list_workspace_pane_entries(workspace_id)

    agent_status_counts: Counter[str] = Counter()
    workspace_agent_status = _herdr_entry_text(workspace, "agent_status")
    if workspace_agent_status is not None:
        agent_status_counts[workspace_agent_status] += 1
    cwd_counts: Counter[str] = Counter()
    agent_count = 0
    focused_panes = 0
    for pane in panes:
        if pane.get("focused"):
            focused_panes += 1
        agent = _herdr_entry_text(pane, "agent")
        if agent is not None:
            agent_count += 1
        agent_status = _herdr_entry_text(pane, "agent_status")
        if agent_status is not None:
            agent_status_counts[agent_status] += 1
        cwd = _herdr_entry_text(pane, "foreground_cwd") or _herdr_entry_text(pane, "cwd")
        if cwd is not None:
            cwd_counts[cwd] += 1
    for tab in tabs:
        agent_status = _herdr_entry_text(tab, "agent_status")
        if agent_status is not None:
            agent_status_counts[agent_status] += 1

    return HerdrWorkspaceSummary(
        name=name,
        workspace_id=workspace_id,
        focused=bool(workspace.get("focused")),
        tabs=len(tabs),
        panes=len(panes),
        agents=agent_count,
        focused_tabs=sum(1 for tab in tabs if tab.get("focused")),
        focused_panes=focused_panes,
        agent_statuses=_format_counts(agent_status_counts),
        cwd=_format_counts(cwd_counts),
    )


def _print_herdr_summary() -> None:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    workspaces = _herdr_workspace_entries_or_exit()
    table = Table(
        title=f"Herdr workspaces ({len(workspaces)})",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Workspace", style="bold cyan")
    table.add_column("ID")
    table.add_column("Focus", justify="center", style="green")
    table.add_column("Tabs", justify="right")
    table.add_column("Panes", justify="right")
    table.add_column("Agents", justify="right", style="green")
    table.add_column("Focused", justify="right")
    table.add_column("Agent Status", overflow="fold")
    table.add_column("CWD", overflow="fold")

    for workspace in [_collect_herdr_summary(workspace=workspace) for workspace in workspaces]:
        table.add_row(
            workspace.name,
            workspace.workspace_id,
            "yes" if workspace.focused else "no",
            str(workspace.tabs),
            str(workspace.panes),
            str(workspace.agents),
            f"{workspace.focused_tabs}/{workspace.focused_panes}",
            workspace.agent_statuses,
            workspace.cwd,
        )
    Console().print(table)


def _tab_id_to_display(tabs: list[JsonObject]) -> dict[str, str]:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    return {
        tab_id: _herdr_backend.tab_display(tab)
        for tab in tabs
        if (tab_id := _herdr_entry_text(tab, "tab_id")) is not None
    }


def _workspace_preview(workspace: JsonObject) -> str:
    workspace_id = _herdr_workspace_id(workspace) or ""
    lines = [
        f"# Workspace: {_herdr_workspace_display_name(workspace) or workspace_id}",
        "",
        "**backend:** herdr",
        f"**id:** {workspace_id}",
        f"**focused:** {'yes' if workspace.get('focused') else 'no'}",
    ]
    number = workspace.get("number")
    if isinstance(number, int):
        lines.append(f"**number:** {number}")
    agent_status = _herdr_entry_text(workspace, "agent_status")
    if agent_status is not None:
        lines.append(f"**agent status:** {agent_status}")
    tab_count = workspace.get("tab_count")
    if isinstance(tab_count, int):
        lines.append(f"**tabs:** {tab_count}")
    pane_count = workspace.get("pane_count")
    if isinstance(pane_count, int):
        lines.append(f"**panes:** {pane_count}")
    return "\n".join(lines)


def _find_herdr_workspace(workspaces: list[JsonObject], name: str) -> JsonObject | None:
    for workspace in workspaces:
        if _herdr_workspace_display_name(workspace) == name:
            return workspace
        if _herdr_workspace_id(workspace) == name:
            return workspace
    return None


def _available_workspace_names(workspaces: list[JsonObject]) -> list[str]:
    names: list[str] = []
    for workspace in workspaces:
        name = _herdr_workspace_display_name(workspace)
        workspace_id = _herdr_workspace_id(workspace)
        if name is not None:
            names.append(name)
        elif workspace_id is not None:
            names.append(workspace_id)
    return names


def _print_herdr_workspace_details(workspace_name: str) -> None:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.table import Table
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    workspaces = _herdr_workspace_entries_or_exit()
    workspace = _find_herdr_workspace(workspaces, workspace_name)
    if workspace is None:
        available = ", ".join(_available_workspace_names(workspaces)) or "none"
        typer.echo(
            f"Error: Herdr workspace '{workspace_name}' not found. Available workspaces: {available}",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)

    workspace_id = _herdr_workspace_id(workspace)
    if workspace_id is None:
        typer.echo(
            f"Error: Herdr workspace '{workspace_name}' did not include a workspace_id.",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)

    console = Console()
    console.print(Markdown(_workspace_preview(workspace)))

    tabs = _herdr_backend.list_workspace_tab_entries(workspace_id)
    panes = _herdr_backend.list_workspace_pane_entries(workspace_id)
    tab_display_by_id = _tab_id_to_display(tabs)

    tab_table = Table(title=f"Herdr tabs ({len(tabs)})")
    tab_table.add_column("#", justify="right")
    tab_table.add_column("Tab", style="bold cyan")
    tab_table.add_column("ID")
    tab_table.add_column("Focused", justify="center")
    tab_table.add_column("Panes", justify="right")
    tab_table.add_column("Agent Status")
    for index, tab in enumerate(tabs, start=1):
        pane_count = tab.get("pane_count")
        tab_table.add_row(
            str(index),
            _herdr_backend.tab_display(tab),
            _herdr_entry_text(tab, "tab_id") or "-",
            "yes" if tab.get("focused") else "no",
            str(pane_count) if isinstance(pane_count, int) else "-",
            _herdr_entry_text(tab, "agent_status") or "-",
        )
    console.print(tab_table)

    pane_table = Table(title=f"Herdr panes ({len(panes)})")
    pane_table.add_column("#", justify="right")
    pane_table.add_column("Pane", style="bold cyan")
    pane_table.add_column("ID")
    pane_table.add_column("Agent")
    pane_table.add_column("Agent Status")
    pane_table.add_column("CWD", overflow="fold")
    pane_table.add_column("Focused", justify="center")
    for index, pane in enumerate(panes, start=1):
        pane_table.add_row(
            str(index),
            _herdr_backend.pane_display(pane, tab_display_by_id),
            _herdr_entry_text(pane, "pane_id") or "-",
            _herdr_entry_text(pane, "agent") or "-",
            _herdr_entry_text(pane, "agent_status") or "-",
            _herdr_entry_text(pane, "foreground_cwd") or _herdr_entry_text(pane, "cwd") or "-",
            "yes" if pane.get("focused") else "no",
        )
    console.print(pane_table)


def _resolve_tmux_session_name(session_name: str | None, choose_session: bool) -> str | None:
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import (
        choose_existing_session_name,
        list_session_names,
    )

    if session_name is not None and choose_session:
        typer.echo("Error: --session cannot be used together with --choose-session.", err=True, color=True)
        raise typer.Exit(code=1)
    if choose_session:
        action, payload = choose_existing_session_name(msg="Choose a tmux session to summarize:")
        if action != "session_name":
            typer.echo(f"Error: {payload}", err=True, color=True)
            raise typer.Exit(code=1)
        return payload
    if session_name is None:
        return None

    available_sessions = list_session_names()
    if session_name not in available_sessions:
        available = ", ".join(available_sessions) if available_sessions else "none"
        typer.echo(
            f"Error: tmux session '{session_name}' not found. Available sessions: {available}",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    return session_name


def _resolve_herdr_workspace_name(workspace_name: str | None, choose_session: bool) -> str | None:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    if workspace_name is not None and choose_session:
        typer.echo("Error: --session cannot be used together with --choose-session.", err=True, color=True)
        raise typer.Exit(code=1)

    workspaces = _herdr_workspace_entries_or_exit()
    if choose_session:
        display_to_workspace = {
            name: workspace
            for workspace in workspaces
            if (name := _herdr_workspace_display_name(workspace)) is not None
        }
        if len(display_to_workspace) == 0:
            typer.echo("Error: No Herdr workspaces are available.", err=True, color=True)
            raise typer.Exit(code=1)
        selection = _herdr_backend.interactive_choose_with_preview(
            msg="Choose a Herdr workspace to summarize:",
            options_to_preview_mapping={
                name: _workspace_preview(entry)
                for name, entry in display_to_workspace.items()
            },
        )
        if selection is None:
            typer.echo("Error: No Herdr workspace selected.", err=True, color=True)
            raise typer.Exit(code=1)
        if isinstance(selection, list):
            selection = selection[0] if selection else None
        if selection not in display_to_workspace:
            typer.echo(f"Error: Unknown Herdr workspace selected: {selection}", err=True, color=True)
            raise typer.Exit(code=1)
        return selection

    if workspace_name is None:
        return None

    if _find_herdr_workspace(workspaces, workspace_name) is None:
        available_names = _available_workspace_names(workspaces)
        available = ", ".join(available_names) if available_names else "none"
        typer.echo(
            f"Error: Herdr workspace '{workspace_name}' not found. Available workspaces: {available}",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    return workspace_name


def summary(
    backend: Annotated[SummaryBackend, typer.Option("--backend", "-b", help="Backend to summarize: tmux, herdr, aoe, or auto.")] = "tmux",
    session: Annotated[str | None, typer.Option("--session", "-s", help="Show details for one tmux session, Herdr workspace, or AoE session by name.")] = None,
    choose_session: Annotated[bool, typer.Option("--choose-session", "-c", help="Choose one tmux session, Herdr workspace, or AoE session interactively and show details.")] = False,
) -> None:
    """Print running terminal session summaries or details for one session."""
    match _resolve_summary_backend(backend):
        case "tmux":
            session_name = _resolve_tmux_session_name(session_name=session, choose_session=choose_session)
            if session_name is None:
                _print_tmux_summary()
                return
            _print_tmux_session_details(session_name=session_name)
        case "herdr":
            workspace_name = _resolve_herdr_workspace_name(workspace_name=session, choose_session=choose_session)
            if workspace_name is None:
                _print_herdr_summary()
                return
            _print_herdr_workspace_details(workspace_name=workspace_name)
        case "aoe":
            session_name = _resolve_aoe_session_name(session_name=session, choose_session=choose_session)
            if session_name is None:
                _print_aoe_summary()
                return
            _print_aoe_session_details(session_name=session_name)
