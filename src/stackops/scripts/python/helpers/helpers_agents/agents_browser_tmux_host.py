from collections.abc import Sequence
import shlex

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_MULTIPLEXER_SESSION_NAME
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserWindowHandle
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common import (
    require_tmux,
    run_optional_tmux_command,
    run_required_tmux_command,
)


def open_tmux_browser_windows(*, launch_id: str, browser_command: Sequence[str], relay_command: Sequence[str] | None) -> BrowserWindowHandle:
    require_tmux()
    endpoint_window_id = _open_window(window_name=f"{launch_id}-endpoint", command=browser_command, label="StackOps browser endpoint")
    window_ids = [endpoint_window_id]
    if relay_command is not None:
        window_ids.append(_open_window(window_name=f"{launch_id}-relay", command=relay_command, label="StackOps browser LAN relay"))
    attach_target = shlex.quote(f"{BROWSER_MULTIPLEXER_SESSION_NAME}:{endpoint_window_id}")
    return BrowserWindowHandle(
        multiplexer="tmux",
        session_name=BROWSER_MULTIPLEXER_SESSION_NAME,
        targets=tuple(window_ids),
        attach_script=f"""if [ -n "${{TMUX:-}}" ]; then tmux switch-client -t {attach_target}; else tmux attach-session -t {attach_target}; fi""",
    )


def open_tmux_relay_window(*, handle: BrowserWindowHandle, launch_id: str, relay_command: Sequence[str]) -> BrowserWindowHandle:
    require_tmux()
    relay_window_id = _open_window(window_name=f"{launch_id}-relay", command=relay_command, label="StackOps browser LAN relay")
    return BrowserWindowHandle(
        multiplexer="tmux",
        session_name=handle.session_name,
        targets=(*handle.targets, relay_window_id),
        attach_script=handle.attach_script,
    )


def close_tmux_browser_windows(*, handle: BrowserWindowHandle) -> None:
    for window_id in handle.targets:
        run_optional_tmux_command(command=("tmux", "kill-window", "-t", window_id))


def _open_window(*, window_name: str, command: Sequence[str], label: str) -> str:
    if run_optional_tmux_command(command=("tmux", "has-session", "-t", f"={BROWSER_MULTIPLEXER_SESSION_NAME}")) is None:
        output = run_required_tmux_command(
            command=("tmux", "new-session", "-d", "-s", BROWSER_MULTIPLEXER_SESSION_NAME, "-n", window_name, "-P", "-F", "#{window_id}")
        )
    else:
        output = run_required_tmux_command(
            command=("tmux", "new-window", "-d", "-t", f"={BROWSER_MULTIPLEXER_SESSION_NAME}:", "-n", window_name, "-P", "-F", "#{window_id}")
        )
    window_id = output.strip()
    run_required_tmux_command(command=("tmux", "set-window-option", "-t", window_id, "remain-on-exit", "on"))
    command_text = shlex.join(command)
    pane_script = f"""printf '%s\\n' {shlex.quote(label)} {shlex.quote(command_text)}; exec {command_text}"""
    run_required_tmux_command(command=("tmux", "send-keys", "-t", window_id, pane_script, "Enter"))
    return window_id
