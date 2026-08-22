from rich import box
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_status import collect_detached_browser_status
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import collect_browser_tmux_status


def show_detached_browser_status() -> None:
    rows = collect_detached_browser_status()
    table = Table(
        title=f"StackOps detached browser status: {len(rows)} tracked launch(es)",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Browser")
    table.add_column("Profile", overflow="fold")
    table.add_column("Host")
    table.add_column("Port", justify="right")
    table.add_column("Window")
    table.add_column("State")
    table.add_column("Browser PID", justify="right")
    table.add_column("Relay PID", justify="right")

    for row in rows:
        launch = row.launch
        relay_process = "-"
        if launch.relay_expected and launch.relay_process_id is None:
            relay_process = "not started"
        elif launch.relay_process_id is not None:
            relay_process = str(launch.relay_process_id) if row.relay_running else f"{launch.relay_process_id} (stopped)"
        table.add_row(
            launch.browser,
            launch.profile,
            launch.host,
            str(launch.port) if not launch.relay_expected else f"{launch.port} -> {launch.browser_port}",
            "- (detached)",
            row.state,
            str(row.browser_process_id) if row.browser_process_id is not None else f"{launch.process_id} (stopped)",
            relay_process,
        )

    Console().print(table)


def show_tmux_browser_status() -> None:
    rows = collect_browser_tmux_status()
    active_launch_ids = {
        row.metadata.launch_id
        for row in rows
        if not row.pane_dead
    }
    rows = tuple(row for row in rows if row.metadata.launch_id in active_launch_ids)
    launch_count = len({row.metadata.launch_id for row in rows})
    window_count = len({row.window_id for row in rows})
    table = Table(
        title=f"StackOps browser tmux: {launch_count} launch(es), {window_count} window(s), {len(rows)} pane(s)",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Session", style="cyan", overflow="fold")
    table.add_column("Launch", overflow="fold")
    table.add_column("Role")
    table.add_column("Browser")
    table.add_column("Profile", overflow="fold")
    table.add_column("Endpoint")
    table.add_column("Window")
    table.add_column("Pane")
    table.add_column("State")
    table.add_column("PID", justify="right")
    table.add_column("Command")
    table.add_column("Profile Path", overflow="fold")

    for row in rows:
        state = "dead" if row.pane_dead else "running"
        endpoint = f"{row.metadata.host}:{row.metadata.port}"
        if row.metadata.lan == "yes":
            endpoint = f"{endpoint} -> 127.0.0.1:{row.metadata.browser_port}"
        table.add_row(
            row.session_name,
            row.metadata.launch_id,
            row.metadata.role,
            row.metadata.browser,
            row.metadata.profile,
            endpoint,
            f"{row.window_index}:{row.window_name}",
            f"{row.pane_index} {row.pane_id}",
            state,
            row.pane_pid,
            row.pane_current_command,
            row.metadata.profile_path,
        )

    Console().print(table)
