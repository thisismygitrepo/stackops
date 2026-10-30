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


def status(
    backend: Annotated[StatusBackend, typer.Option("--backend", help="Session-manager backend to inspect: tuios, herdr or aoe. AoE uses its current profile.")] = "tuios",
    session: Annotated[list[str] | None, typer.Option("--session", "-s", help="Session name or stable ID; repeat to select several. Default: all live local sessions, including detached sessions. AoE scope is its current profile.")] = None,
    window: Annotated[list[str] | None, typer.Option("--window", "-w", help="Window/pane name or stable ID; AoE session name or ID. Repeat to select several.")] = None,
    exclude_window: Annotated[list[str] | None, typer.Option("--exclude-window", help="Window/pane ID or name to omit; AoE session name or ID. Repeat as needed.")] = None,
    harness: Annotated[list[str] | None, typer.Option("--harness", "-a", help="Agent harness to include; repeat as needed. 'claude' is an alias for 'claude-code'.")] = None,
    state: Annotated[list[str] | None, typer.Option("--state", help="Filter working, waiting, blocked, idle, completed, failed, unknown or unavailable; repeat as needed. completed also matches tasks reported completed while their live agents are idle.")] = None,
    include_self: Annotated[bool, typer.Option("--include-self/--exclude-self", help="Include the observer's own pane. Default: exclude it using pane/process identity.")] = False,
    history: Annotated[HistoryMode, typer.Option("--history", help="auto: linked transcripts or AoE structured history, otherwise hooks where supported; transcripts: linked files or AoE structured history; hooks: TUIOS only; none: skip history.")] = "auto",
    lines: Annotated[int, typer.Option("--lines", min=0, help="Lines to capture per agent. TUIOS and AoE tmux include scrollback; Herdr includes retained scrollback only for idle agents without a linked transcript (its scrollback reads are slow), otherwise the visible viewport; AoE ACP workers have no pane. 0 captures all TUIOS scrollback, Herdr's default retained output or the AoE viewport.")] = 200,
    messages: Annotated[int, typer.Option("--messages", min=0, help="Newest retained human/context messages per agent, in chronological order. 0 keeps all available messages.")] = 0,
    text_limit: Annotated[int, typer.Option("--text-limit", min=0, help="Character limit per message or evidence text. Truncation is marked. 0 keeps full text.")] = 8000,
    events: Annotated[int, typer.Option("--events", min=1, max=256, help="Maximum TUIOS hook events to inspect per agent; these are bounded and may be abbreviated.")] = 256,
    timeout: Annotated[float, typer.Option("--timeout", min=0.1, help="Timeout in seconds for each external inspection command.")] = 10.0,
    workers: Annotated[int, typer.Option("--workers", min=1, max=64, help="Maximum concurrent read-only inspection operations.")] = 8,
    server: Annotated[str | None, typer.Option("--server", help="Named local TUIOS daemon to inspect. Default: TUIOS's current/default daemon.")] = None,
    claude_home: Annotated[Path | None, typer.Option("--claude-home", file_okay=False, help="Claude metadata/transcript root. Default: CLAUDE_CONFIG_DIR, otherwise ~/.claude.")] = None,
    codex_home: Annotated[Path | None, typer.Option("--codex-home", file_okay=False, help="Codex transcript root for registered session IDs. Default: CODEX_HOME, otherwise ~/.codex. Open-file metadata can link other homes.")] = None,
    output_format: Annotated[StatusFormat, typer.Option("--format", "-f", help="Output format. JSON contains structured evidence and full extracted history subject to the requested limits.")] = "table",
    json_output: Annotated[bool, typer.Option("--json", help="Shortcut for --format json; incompatible with --format markdown.")] = False,
    rich_output: Annotated[bool, typer.Option("--rich-output", help="Print a styled terminal overview and agent cards with colour, history and evidence. Cannot combine with JSON or Markdown. File output has no ANSI colours.")] = False,
    output: Annotated[Path | None, typer.Option("--output", "-o", dir_okay=False, help="Write the report to a private file instead of stdout. Existing files require --force.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Allow replacing an existing --output file; agent sessions are never modified.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_agents.agents_status_collect import collect_status
    from stackops.scripts.python.helpers.helpers_agents.agents_status_render import render_status, write_status_output

    if json_output and output_format not in {"table", "json"}:
        raise typer.BadParameter("--json cannot be combined with --format markdown.")
    if rich_output and (json_output or output_format != "table"):
        raise typer.BadParameter("--rich-output cannot be combined with --json or --format json/markdown.")
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
        sessions=tuple(session or ()), windows=tuple(window or ()), exclude_windows=tuple(exclude_window or ()),
        harnesses=tuple("claude-code" if value.lower() == "claude" else value.lower() for value in harness or ()),
        states=selected_states, include_self=include_self, history=history, capture_lines=lines,
        message_limit=messages, text_limit=text_limit, event_limit=events, timeout=timeout, workers=workers,
        server=server, claude_home=(claude_home or Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))).expanduser(),
        codex_home=(codex_home or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))).expanduser(),
    )
    try:
        snapshot = collect_status(options=options)
        if rich_output:
            from stackops.scripts.python.helpers.helpers_agents.agents_status_rich_output import print_rich_status

            print_rich_status(snapshot=snapshot, output=output, force=force)
            return
        report = render_status(snapshot=snapshot, output_format="json" if json_output else output_format)
        write_status_output(report=report, output=output, force=force)
    except (OSError, RuntimeError, ValueError) as error:
        typer.echo(f"""Could not inspect agent status: {error}""", err=True)
        raise typer.Exit(code=1) from error
