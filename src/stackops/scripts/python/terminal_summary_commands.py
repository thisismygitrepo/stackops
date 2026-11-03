from typing import Annotated

import typer

from stackops.utils.default_multiplexer import DEFAULT_SESSION_MULTIPLEXER_HELP
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexerOption


def summary(
    backend: Annotated[SessionMultiplexerOption | None, typer.Option("--backend", "-b", help=f"Session multiplexer to summarize: tmux/t, herdr/h, tuios/u, aoe/e, or zellij/z (Zellij 0.45+). {DEFAULT_SESSION_MULTIPLEXER_HELP}")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="Show details for one backend session or workspace by name.")] = None,
    choose_session: Annotated[bool, typer.Option("--choose-session", "-c", help="Choose one backend session or workspace interactively and show details.")] = False,
    show_tabs: Annotated[bool, typer.Option("--tabs", "-t", help="Include tab/window and pane details for every session (tmux, Herdr, TUIOS, and Zellij).")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print structured session summaries as JSON without a picker; --tabs includes pane details.")] = False,
) -> None:
    """Print running terminal session summaries or details for one session."""
    if json_output:
        import json
        import subprocess
        import sys
        from contextlib import redirect_stdout

        from stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers import resolve_session_backend
        from stackops.scripts.python.helpers.helpers_sessions.terminal_summary_json import collect_summary

        if choose_session:
            raise typer.BadParameter("--choose-session cannot be combined with --json. Pass --session instead.")
        if session is not None and not session.strip():
            raise typer.BadParameter("--session must not be blank.")
        try:
            with redirect_stdout(sys.stderr):
                resolved_backend = resolve_session_backend(backend)
                records = collect_summary(backend=resolved_backend, session=session, show_tabs=show_tabs)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            typer.echo(f"""Error: {error}""", err=True)
            raise typer.Exit(code=1) from error
        typer.echo(json.dumps({"backend": resolved_backend, "sessions": records}, ensure_ascii=False))
        return

    from stackops.scripts.python.terminal_summary import summary as print_summary

    print_summary(backend=backend, session=session, choose_session=choose_session, show_tabs=show_tabs)
