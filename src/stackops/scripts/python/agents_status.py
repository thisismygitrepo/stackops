import os
from pathlib import Path
from typing import Annotated, get_args

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import (
    AgentStatus,
    HistoryMode,
    StatusFormat,
    StatusOptions,
)
from stackops.utils.default_multiplexer import DEFAULT_AGENT_MULTIPLEXER_HELP
from stackops.utils.schemas.config.multiplexer_types import AgentStatusBackend
from stackops.scripts.python.helpers.helpers_agents.constants import (
    AGENTS_STATUS_BTW_TIMEOUT_SECONDS,
    AGENTS_STATUS_EVENT_LIMIT,
    AGENTS_STATUS_TIMEOUT_SECONDS,
    AGENTS_STATUS_WORKERS,
)


def status(
    backend: Annotated[AgentStatusBackend | None, typer.Option("--backend", "-b", help=f"Agent backend to inspect: tuios, herdr, aoe or t3. AoE uses its current profile. t3 reads unsettled threads on the local T3 Code server; it has no sessions, layouts, tabs or panes, so --session, --layout, --tab, --pane, --exclude-pane and --server are rejected and --lines does not apply. {DEFAULT_AGENT_MULTIPLEXER_HELP}")] = None,
    session: Annotated[list[str] | None, typer.Option("--session", "-s", help="Native manager session name or ID; Herdr's outer session, TUIOS session, or AoE session in the current profile. Default: all live local sessions, including detached sessions. Repeat for alternatives.")] = None,
    layout: Annotated[list[str] | None, typer.Option("--layout", "-l", help="Layout scope: TUIOS session name/ID; Herdr workspace label/ID/number; AoE full group path. Repeat for alternatives.")] = None,
    tab: Annotated[list[str] | None, typer.Option("--tab", "-t", help="Layout tab: TUIOS workspace name/number; Herdr tab label/ID; AoE session title/ID. Repeat for alternatives.")] = None,
    window: Annotated[list[str] | None, typer.Option("--pane", "-p", help="Layout pane: TUIOS window name/ID; Herdr pane label/title/ID; AoE session title/ID (one runtime per tab). Repeat for alternatives.")] = None,
    exclude_window: Annotated[list[str] | None, typer.Option("--exclude-pane", "-x", help="Pane name or ID to omit, using the same mapping as --pane. Repeat as needed.")] = None,
    agent_session: Annotated[list[str] | None, typer.Option("--agent-session", "-A", help="Reported agent name or conversation ID, when available: TUIOS registered name (also pane name), Herdr agent name, AoE session title/ID. Repeat for alternatives.")] = None,
    harness: Annotated[list[str] | None, typer.Option("--harness", "-a", help="Agent harness to include; repeat as needed. 'claude' is an alias for 'claude-code'.")] = None,
    state: Annotated[list[str] | None, typer.Option("--state", "-S", help="Filter working, waiting, blocked, idle, completed, failed, unknown or unavailable; repeat as needed. completed also matches tasks reported completed while their live agents are idle.")] = None,
    include_self: Annotated[bool, typer.Option("--include-self", "-i", help="Include the observer's own pane. Default: exclude it using pane/process identity.")] = False,
    history: Annotated[HistoryMode, typer.Option("--history", "-H", help="auto: use available linked transcripts, AoE structured history or supported hooks; none: skip history.")] = "auto",
    lines: Annotated[int, typer.Option("--lines", "-n", min=0, help="Lines to capture per agent. TUIOS and AoE tmux include scrollback; Herdr includes retained scrollback only for idle agents without a linked transcript (its scrollback reads are slow), otherwise the visible viewport; AoE ACP workers have no pane. 0 captures all TUIOS scrollback, Herdr's default retained output or the AoE viewport.")] = 200,
    messages: Annotated[int, typer.Option("--messages", "-m", min=0, help="Newest retained human/context messages per agent, in chronological order. 0 keeps all available messages.")] = 0,
    text_limit: Annotated[int, typer.Option("--text-limit", "-T", min=0, help="Character limit per message or evidence text. Truncation is marked. 0 keeps full text.")] = 8000,
    server: Annotated[str | None, typer.Option("--server", "-d", help="Named local TUIOS daemon to inspect. Default: TUIOS's current/default daemon.")] = None,
    output_format: Annotated[StatusFormat, typer.Option("--format", "-f", help="Output format: table, rich (styled overview and agent cards), json or markdown. JSON includes structured evidence and extracted history subject to the requested limits. File output has no ANSI colours.")] = "table",
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print structured JSON; shorthand for --format json.")] = False,
    output: Annotated[Path | None, typer.Option("--output", "-o", dir_okay=False, help="Write the report to a private file instead of stdout. Existing files require --force.")] = None,
    force: Annotated[bool, typer.Option("--force", "-F", help="Allow replacing an existing --output file; agent sessions are never modified.")] = False,
    btw: Annotated[bool, typer.Option("--btw", "-w", help="By the way: also ask each shown agent two side questions, its status and what it is working on, in a fork that leaves its main conversation untouched. Claude Code uses a non-persisted --fork-session without tools; Codex uses an ephemeral read-only exec fork; T3 Code forks the thread's latest completed run and archives the fork. Other harnesses, or agents without a linked conversation, report the side question as unavailable. Forks use model turns and can take minutes.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_agents.agents_status_collect import collect_status
    from stackops.scripts.python.helpers.helpers_agents.agents_status_render import render_status, write_status_output
    from stackops.utils.default_multiplexer import resolve_agent_multiplexer

    if json_output:
        if output_format not in ("table", "json"):
            raise typer.BadParameter("--json cannot be combined with a non-JSON --format.", param_hint="--json")
        output_format = "json"
    if force and output is None:
        raise typer.BadParameter("--force requires --output.")
    if backend == "t3":
        layout_flags = [
            flag for flag, value in (
                ("--session", session), ("--layout", layout), ("--tab", tab), ("--pane", window), ("--exclude-pane", exclude_window), ("--server", server),
            ) if value
        ]
        if layout_flags:
            raise typer.BadParameter(
                f"""{', '.join(layout_flags)} cannot be used with --backend t3. T3 Code has projects and threads, not sessions, layouts, tabs or panes. """
                """Select threads with --agent-session (thread title or ID), --harness or --state instead.""",
                param_hint="--backend",
            )
    try:
        resolved_backend: AgentStatusBackend = "t3" if backend == "t3" else resolve_agent_multiplexer(multiplexer=backend)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--backend") from error
    if resolved_backend != "tuios" and server is not None:
        raise typer.BadParameter("--server is only supported by TUIOS. Use --session to select sessions.", param_hint="--server")
    selected_states = tuple(value.lower() for value in state or ())
    supported_states = get_args(AgentStatus)
    if invalid_states := set(selected_states).difference(supported_states):
        raise typer.BadParameter(
            f"""Unknown status: {', '.join(sorted(invalid_states))}. Choose from {', '.join(supported_states)}.""",
            param_hint="--state",
        )
    options = StatusOptions(
        backend=resolved_backend,
        sessions=tuple(session or ()), layouts=tuple(layout or ()), tabs=tuple(tab or ()),
        windows=tuple(window or ()), exclude_windows=tuple(exclude_window or ()), agent_sessions=tuple(agent_session or ()),
        harnesses=tuple("claude-code" if value.lower() == "claude" else value.lower() for value in harness or ()),
        states=selected_states, include_self=include_self, history=history, capture_lines=lines,
        message_limit=messages, text_limit=text_limit, event_limit=AGENTS_STATUS_EVENT_LIMIT,
        timeout=AGENTS_STATUS_TIMEOUT_SECONDS, workers=AGENTS_STATUS_WORKERS,
        server=server, claude_home=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))).expanduser(),
        codex_home=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser(),
    )
    try:
        if resolved_backend == "t3":
            from stackops.scripts.python.helpers.helpers_agents.agents_status_t3 import collect_t3_status

            snapshot = collect_t3_status(options=options)
        else:
            snapshot = collect_status(options=options)
        if btw:
            from stackops.scripts.python.helpers.helpers_agents.agents_status_btw import ask_btw

            typer.echo(f"""Asking {len(snapshot.agents)} agents two by-the-way side questions each in forked conversations…""", err=True)
            snapshot = ask_btw(snapshot=snapshot, workers=AGENTS_STATUS_WORKERS, timeout=AGENTS_STATUS_BTW_TIMEOUT_SECONDS, text_limit=text_limit)
        if output_format == "rich":
            from stackops.scripts.python.helpers.helpers_agents.agents_status_rich_output import print_rich_status

            print_rich_status(snapshot=snapshot, output=output, force=force)
            return
        report = render_status(snapshot=snapshot, output_format=output_format)
        write_status_output(report=report, output=output, force=force)
    except (OSError, RuntimeError, ValueError) as error:
        typer.echo(f"""Could not inspect agent status: {error}""", err=True)
        raise typer.Exit(code=1) from error
