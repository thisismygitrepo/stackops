from typing import Annotated

import typer

from stackops.utils.default_multiplexer import DEFAULT_SESSION_MULTIPLEXER_HELP
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexerOption


def summary(
    backend: Annotated[SessionMultiplexerOption | None, typer.Option("--backend", "-b", help=f"Session multiplexer to summarize: tmux/t, herdr/h, tuios/u, or aoe/e. {DEFAULT_SESSION_MULTIPLEXER_HELP}")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="Show details for one backend session or workspace by name.")] = None,
    choose_session: Annotated[bool, typer.Option("--choose-session", "-c", help="Choose one backend session or workspace interactively and show details.")] = False,
    show_tabs: Annotated[bool, typer.Option("--tabs", "-t", help="Include tab/window and pane details for every session (tmux, Herdr, and TUIOS).")] = False,
) -> None:
    """Print running terminal session summaries or details for one session."""
    from stackops.scripts.python.terminal_summary import summary as print_summary

    print_summary(backend=backend, session=session, choose_session=choose_session, show_tabs=show_tabs)
