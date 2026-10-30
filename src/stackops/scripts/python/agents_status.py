import os
from pathlib import Path
from typing import Annotated, get_args

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import (
    AgentStatus,
    HistoryMode,
    StatusBackend,
    StatusFormat,
    StatusOptions,
)
from stackops.scripts.python.helpers.helpers_agents.constants import (
    AGENTS_STATUS_EVENT_LIMIT,
    AGENTS_STATUS_TIMEOUT_SECONDS,
    AGENTS_STATUS_WORKERS,
)


def status(
    backend: Annotated[StatusBackend, typer.Option("--backend", help="Session-manager backend to inspect: tuios, herdr or aoe. AoE uses its current profile.")] = "tuios",
    session: Annotated[list[str] | None, typer.Option("--session", "-s", help="Native manager session name or ID; Herdr's outer session, TUIOS session, or AoE session in the current profile. Default: all live local sessions, including detached sessions. Repeat for alternatives.")] = None,
    layout: Annotated[list[str] | None, typer.Option("--layout", help="Layout scope: TUIOS session name/ID; Herdr workspace label/ID/number; AoE full group path. Repeat for alternatives.")] = None,
    tab: Annotated[list[str] | None, typer.Option("--tab", "-t", help="Layout tab: TUIOS workspace name/number; Herdr tab label/ID; AoE session title/ID. Repeat for alternatives.")] = None,
    window: Annotated[list[str] | None, typer.Option("--pane", "-p", help="Layout pane: TUIOS window name/ID; Herdr pane label/title/ID; AoE session title/ID (one runtime per tab). Repeat for alternatives.")] = None,
    exclude_window: Annotated[list[str] | None, typer.Option("--exclude-pane", help="Pane name or ID to omit, using the same mapping as --pane. Repeat as needed.")] = None,
    agent_session: Annotated[list[str] | None, typer.Option("--agent-session", help="Reported agent name or conversation ID, when available: TUIOS registered name (also pane name), Herdr agent name, AoE session title/ID. Repeat for alternatives.")] = None,
    harness: Annotated[list[str] | None, typer.Option("--harness", "-a", help="Agent harness to include; repeat as needed. 'claude' is an alias for 'claude-code'.")] = None,
    state: Annotated[list[str] | None, typer.Option("--state", help="Filter working, waiting, blocked, idle, completed, failed, unknown or unavailable; repeat as needed. completed also matches tasks reported completed while their live agents are idle.")] = None,
    include_self: Annotated[bool, typer.Option("--include-self", help="Include the observer's own pane. Default: exclude it using pane/process identity.")] = False,
    history: Annotated[HistoryMode, typer.Option("--history", help="auto: use available linked transcripts, AoE structured history or supported hooks; none: skip history.")] = "auto",
    lines: Annotated[int, typer.Option("--lines", min=0, help="Lines to capture per agent. TUIOS and AoE tmux include scrollback; Herdr includes retained scrollback only for idle agents without a linked transcript (its scrollback reads are slow), otherwise the visible viewport; AoE ACP workers have no pane. 0 captures all TUIOS scrollback, Herdr's default retained output or the AoE viewport.")] = 200,
    messages: Annotated[int, typer.Option("--messages", min=0, help="Newest retained human/context messages per agent, in chronological order. 0 keeps all available messages.")] = 0,
    text_limit: Annotated[int, typer.Option("--text-limit", min=0, help="Character limit per message or evidence text. Truncation is marked. 0 keeps full text.")] = 8000,
    server: Annotated[str | None, typer.Option("--server", help="Named local TUIOS daemon to inspect. Default: TUIOS's current/default daemon.")] = None,
    output_format: Annotated[StatusFormat, typer.Option("--format", "-f", help="Output format: table, rich (styled overview and agent cards), json or markdown. JSON includes structured evidence and extracted history subject to the requested limits. File output has no ANSI colours.")] = "table",
    output: Annotated[Path | None, typer.Option("--output", "-o", dir_okay=False, help="Write the report to a private file instead of stdout. Existing files require --force.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Allow replacing an existing --output file; agent sessions are never modified.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_agents.agents_status_collect import collect_status
    from stackops.scripts.python.helpers.helpers_agents.agents_status_render import render_status, write_status_output

    if force and output is None:
        raise typer.BadParameter("--force requires --output.")
    if backend != "tuios" and server is not None:
        raise typer.BadParameter("--server is only supported by TUIOS. Use --session to select sessions.", param_hint="--server")
    selected_states = tuple(value.lower() for value in state or ())
    supported_states = get_args(AgentStatus)
    if invalid_states := set(selected_states).difference(supported_states):
        raise typer.BadParameter(
            f"""Unknown status: {', '.join(sorted(invalid_states))}. Choose from {', '.join(supported_states)}.""",
            param_hint="--state",
        )
    options = StatusOptions(
        backend=backend,
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
        snapshot = collect_status(options=options)
        if output_format == "rich":
            from stackops.scripts.python.helpers.helpers_agents.agents_status_rich_output import print_rich_status

            print_rich_status(snapshot=snapshot, output=output, force=force)
            return
        report = render_status(snapshot=snapshot, output_format=output_format)
        write_status_output(report=report, output=output, force=force)
    except (OSError, RuntimeError, ValueError) as error:
        typer.echo(f"""Could not inspect agent status: {error}""", err=True)
        raise typer.Exit(code=1) from error
