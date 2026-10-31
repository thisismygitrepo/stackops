import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from stackops.scripts.python.terminal_summary_models import ResolvedSummaryBackend


type LaunchVerb = Literal["started", "added"]


@dataclass(frozen=True, slots=True)
class LaunchedPaneRow:
    location: str
    tab_name: str
    pane_name: str
    handle: str
    command: str
    start_dir: str


@dataclass(frozen=True, slots=True)
class _BackendLabels:
    container: str
    location_header: str
    handle_header: str
    pane_noun: str
    tab_noun: str
    attach_hint: str | None


def _backend_labels(backend: ResolvedSummaryBackend, session_name: str) -> _BackendLabels:
    quoted_name = shlex.quote(session_name)
    match backend:
        case "tuios":
            return _BackendLabels(container="TUIOS session", location_header="WS", handle_header="Window ID", pane_noun="window", tab_noun="workspace", attach_hint=f"""tuios attach -- {quoted_name}""")
        case "tmux":
            return _BackendLabels(container="tmux session", location_header="Win", handle_header="Pane ID", pane_noun="pane", tab_noun="window", attach_hint=f"""tmux attach -t {quoted_name}""")
        case "herdr":
            return _BackendLabels(container="Herdr workspace", location_header="Tab ID", handle_header="Pane ID", pane_noun="pane", tab_noun="tab", attach_hint=None)
        case "aoe":
            return _BackendLabels(container="AoE group", location_header="Tool", handle_header="Session", pane_noun="session", tab_noun="tab", attach_hint="aoe session attach <session>")


def print_launch_table(backend: ResolvedSummaryBackend, session_name: str, rows: Sequence[LaunchedPaneRow], verb: LaunchVerb) -> None:
    labels = _backend_labels(backend=backend, session_name=session_name)
    table = Table(
        title=f"""🚀 {labels.container} [bold]{escape(session_name)}[/bold] {verb}""",
        caption=f"""{len(rows)} {labels.pane_noun}(s) across {len({row.tab_name for row in rows})} {labels.tab_noun}(s)""",
        box=box.ROUNDED,
        title_style="green",
        caption_style="dim",
        header_style="bold cyan",
    )
    table.add_column(labels.location_header, style="magenta", no_wrap=True)
    table.add_column("Tab", style="bold", overflow="fold")
    table.add_column("Pane", overflow="fold")
    table.add_column(labels.handle_header, style="dim", no_wrap=True)
    table.add_column("Command", style="yellow", overflow="fold")
    table.add_column("Start dir", style="blue", overflow="fold")
    for row in rows:
        table.add_row(
            escape(row.location),
            escape(row.tab_name),
            escape(row.pane_name),
            escape(row.handle),
            escape(row.command),
            escape(row.start_dir),
        )
    console = Console()
    console.print(table)
    if labels.attach_hint is not None:
        console.print(f"""[dim]attach:[/dim] [bold]{escape(labels.attach_hint)}[/bold]""", soft_wrap=True)
