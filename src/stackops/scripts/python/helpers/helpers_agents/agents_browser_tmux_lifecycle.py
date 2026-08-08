import os
import shlex
import subprocess
import time

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common import (
    run_optional_tmux_command,
    run_required_tmux_command,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import (
    STACKOPS_BROWSER_TMUX_SESSION_NAME,
    BrowserTmuxLaunch,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_status import collect_browser_tmux_status


def build_attach_or_switch_command(*, session_name: str, window_name: str) -> tuple[str, ...]:
    target = f"{session_name}:{window_name}"
    if os.environ.get("TMUX"):
        return ("tmux", "switch-client", "-t", target)
    return ("tmux", "attach-session", "-t", target)


def attach_or_switch_tmux_window(*, session_name: str, window_name: str) -> None:
    command = build_attach_or_switch_command(session_name=session_name, window_name=window_name)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"""tmux attach/switch failed with exit code {result.returncode}: {shlex.join(command)}""")


def prune_dead_browser_tmux_launches() -> None:
    rows = collect_browser_tmux_status()
    launch_ids = {row.metadata.launch_id for row in rows}
    window_ids_to_kill: set[str] = set()
    for launch_id in launch_ids:
        launch_rows = tuple(row for row in rows if row.metadata.launch_id == launch_id)
        endpoint_is_running = any(row.metadata.role == "endpoint" and not row.pane_dead for row in launch_rows)
        for row in launch_rows:
            if row.pane_dead or not endpoint_is_running:
                window_ids_to_kill.add(row.window_id)
    for window_id in window_ids_to_kill:
        run_required_tmux_command(command=("tmux", "kill-window", "-t", window_id))


def assert_browser_tmux_window_running(*, window_name: str, process_label: str) -> None:
    matching_rows = tuple(row for row in collect_browser_tmux_status() if row.window_name == window_name)
    if not matching_rows or any(row.pane_dead for row in matching_rows):
        raise RuntimeError(f"{process_label} exited before its tmux window {window_name} became ready")
    time.sleep(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
    matching_rows = tuple(row for row in collect_browser_tmux_status() if row.window_name == window_name)
    if not matching_rows or any(row.pane_dead for row in matching_rows):
        raise RuntimeError(f"{process_label} exited while its tmux window {window_name} became ready")


def close_browser_tmux_launch(*, launch: BrowserTmuxLaunch) -> None:
    window_names = tuple(
        window_name
        for window_name in (launch.relay_window_name, launch.browser_window_name)
        if window_name is not None
    )
    for window_name in window_names:
        target = f"{STACKOPS_BROWSER_TMUX_SESSION_NAME}:{window_name}"
        result = run_optional_tmux_command(command=("tmux", "kill-window", "-t", target))
        if result is None:
            return
