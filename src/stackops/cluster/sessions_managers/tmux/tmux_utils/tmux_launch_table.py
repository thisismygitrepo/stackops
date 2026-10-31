from stackops.cluster.sessions_managers.session_launch_table import LaunchedPaneRow, print_launch_table
from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common import shell_quote
from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution import run_tmux_commands
from stackops.utils.schemas.layouts.layout_types import TabConfig


def _tab_rows(session_name: str, tab: TabConfig) -> list[LaunchedPaneRow]:
    window_target = shell_quote(f"""{session_name}:{tab['tabName']}""")
    pane_format = shell_quote("#{window_index}\t#{pane_id}")
    output = run_tmux_commands(commands=[f"""tmux list-panes -t {window_target} -F {pane_format}"""], timeout_seconds=5.0)[0].stdout
    pane_entries = [line.split("\t") for line in output.splitlines() if line.strip()]
    return [
        LaunchedPaneRow(
            location=window_index,
            tab_name=tab["tabName"],
            pane_name=pane["paneName"],
            handle=pane_id,
            command=pane["command"],
            start_dir=pane["startDir"],
        )
        for pane, (window_index, pane_id) in zip(tab["panes"], pane_entries, strict=True)
    ]


def print_tmux_launch_table(session_name: str, tabs: list[TabConfig]) -> None:
    print_launch_table(
        backend="tmux",
        session_name=session_name,
        rows=[row for tab in tabs for row in _tab_rows(session_name=session_name, tab=tab)],
        verb="started",
    )
