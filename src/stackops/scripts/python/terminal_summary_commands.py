from typing import Annotated

import typer

from stackops.scripts.python.terminal_summary_models import LegacySummarizeBackend, SummarizeVocabulary, SummaryBackend


def summary(
    backend: Annotated[SummaryBackend, typer.Option("--backend", "-b", help="Backend to summarize: tmux, herdr, aoe, tuios, or auto.")] = "tmux",
    session: Annotated[str | None, typer.Option("--session", "-s", help="Show details for one backend session or workspace by name.")] = None,
    choose_session: Annotated[bool, typer.Option("--choose-session", "-c", help="Choose one backend session or workspace interactively and show details.")] = False,
    show_tabs: Annotated[bool, typer.Option("--tabs", "-t", help="Include tab/window and pane details for every session (tmux, Herdr, and TUIOS).")] = False,
) -> None:
    """Print running terminal session summaries or details for one session."""
    from stackops.scripts.python.terminal_summary import summary as print_summary

    print_summary(backend=backend, session=session, choose_session=choose_session, show_tabs=show_tabs)


def summarize(
    layout_path: Annotated[str, typer.Argument(..., help="Path to the layout.json file")],
    vocabulary: Annotated[
        SummarizeVocabulary,
        typer.Option("--vocabulary", "-v", help="Output vocabulary to use: layout or herdr."),
    ] = "layout",
    backend: Annotated[
        LegacySummarizeBackend | None,
        typer.Option("--backend", "-b", help="Deprecated alias for --vocabulary.", hidden=True),
    ] = None,
    show_tabs: Annotated[bool, typer.Option("--tabs", "-t", help="Show tab names, directories, commands, and weights.")] = False,
) -> None:
    """Summarize a layout file with counts for layouts and tabs."""
    from stackops.scripts.python.terminal_summarize import summarize as print_layout_summary

    print_layout_summary(layout_path=layout_path, vocabulary=vocabulary, backend=backend, show_tabs=show_tabs)
