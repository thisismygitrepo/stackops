from collections.abc import Sequence
from contextlib import ExitStack
import platform
import re
import shlex
from uuid import uuid4

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution import build_tmux_attach_or_switch_handoff_script
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_MULTIPLEXER_SESSION_NAME, BROWSER_TMUX_OWNER_OPTION
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserWindowHandle
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common import (
    require_tmux,
    run_optional_tmux_command,
    run_required_tmux_command,
)
from stackops.scripts.python.helpers.helpers_sessions._attach_common import quote_powershell


def open_tmux_browser_windows(*, launch_id: str, browser_command: Sequence[str], relay_command: Sequence[str] | None) -> BrowserWindowHandle:
    require_tmux()
    session_name = BROWSER_MULTIPLEXER_SESSION_NAME
    with ExitStack() as rollback:
        endpoint_target = _open_window(window_name=f"{launch_id}-endpoint", command=browser_command, label="StackOps browser endpoint")
        rollback.callback(_close_window, session_name=session_name, target=endpoint_target)
        targets = [endpoint_target]
        if relay_command is not None:
            relay_target = _open_window(window_name=f"{launch_id}-relay", command=relay_command, label="StackOps browser LAN relay")
            rollback.callback(_close_window, session_name=session_name, target=relay_target)
            targets.append(relay_target)
        endpoint_window_id = endpoint_target.partition("/")[0]
        handle = BrowserWindowHandle(
            multiplexer="tmux",
            session_name=session_name,
            targets=tuple(targets),
            attach_script=build_tmux_attach_or_switch_handoff_script(session_name=f"{session_name}:{endpoint_window_id}"),
        )
        rollback.pop_all()
    return handle


def open_tmux_relay_window(*, handle: BrowserWindowHandle, launch_id: str, relay_command: Sequence[str]) -> BrowserWindowHandle:
    require_tmux()
    relay_target = _open_window(window_name=f"{launch_id}-relay", command=relay_command, label="StackOps browser LAN relay")
    return BrowserWindowHandle(
        multiplexer="tmux",
        session_name=handle.session_name,
        targets=(*handle.targets, relay_target),
        attach_script=handle.attach_script,
    )


def close_tmux_browser_windows(*, handle: BrowserWindowHandle) -> None:
    for target in handle.targets:
        _close_window(session_name=handle.session_name, target=target)


def _close_window(*, session_name: str, target: str) -> None:
    match = re.fullmatch(r"(@[0-9]+)/([0-9a-f]{32})", target)
    if match is None:
        return  # An ID-only record cannot identify a window after a server restart.
    window_id, owner = match.groups()
    window = f"={session_name}:{window_id}"
    owner_matches = f"#{{==:#{{{BROWSER_TMUX_OWNER_OPTION}}},{owner}}}"
    run_optional_tmux_command(command=("tmux", "if-shell", "-F", "-t", window, owner_matches, f"kill-window -t {shlex.quote(window)}"))


def _open_window(*, window_name: str, command: Sequence[str], label: str) -> str:
    owner = uuid4().hex
    setup_window = f"={BROWSER_MULTIPLEXER_SESSION_NAME}:={owner}"
    if run_optional_tmux_command(command=("tmux", "has-session", "-t", f"={BROWSER_MULTIPLEXER_SESSION_NAME}")) is None:
        create = ("new-session", "-d", "-s", BROWSER_MULTIPLEXER_SESSION_NAME)
    else:
        create = ("new-window", "-d", "-t", f"={BROWSER_MULTIPLEXER_SESSION_NAME}:")
    output = run_required_tmux_command(
        command=(
            "tmux", *create, "-n", owner, "-P", "-F", "#{window_id}",
            ";", "set-option", "-w", "-t", setup_window, BROWSER_TMUX_OWNER_OPTION, owner,
            ";", "set-option", "-w", "-t", setup_window, "remain-on-exit", "on",
            ";", "send-keys", "-t", setup_window, _pane_script(command=command, label=label), "Enter",
            ";", "rename-window", "-t", setup_window, window_name,
        )
    )
    return f"{output.strip()}/{owner}"


def _pane_script(*, command: Sequence[str], label: str) -> str:
    if platform.system() == "Windows":
        command_text = "& " + " ".join(quote_powershell(part) for part in command)
        return f"""Write-Output {quote_powershell(label)} {quote_powershell(command_text)}; {command_text}"""
    command_text = shlex.join(command)
    return f"""printf '%s\\n' {shlex.quote(label)} {shlex.quote(command_text)}; exec {command_text}"""
