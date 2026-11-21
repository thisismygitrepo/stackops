from collections.abc import Sequence
import platform
import subprocess

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserMultiplexer, BrowserRuntime, BrowserRuntimeOption
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserWindowHandle
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_host import (
    close_tmux_browser_windows,
    open_tmux_browser_windows,
    open_tmux_relay_window,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tuios_host import (
    close_tuios_browser_windows,
    open_tuios_browser_windows,
    open_tuios_relay_window,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_zellij_host import (
    close_zellij_browser_windows,
    open_zellij_browser_windows,
    open_zellij_relay_window,
)
from stackops.utils.default_multiplexer import resolve_session_multiplexer


def resolve_browser_runtime(*, runtime: BrowserRuntimeOption | None) -> BrowserRuntime:
    match runtime:
        case "detached" | "d":
            return "detached"
        case "tmux" | "t":
            return "tmux"
        case "tuios" | "u":
            return "tuios"
        case "zellij" | "z":
            return "zellij"
        case None:
            multiplexer = resolve_session_multiplexer(multiplexer=None)
            match multiplexer:
                case "tmux" | "tuios" | "zellij":
                    return multiplexer
                case "herdr" | "aoe":
                    raise ValueError(
                        f"Browser launches run on tmux, tuios, zellij or detached, but default_session_multiplexer is {multiplexer}; pass --runtime"
                    )


def open_browser_windows(
    *, multiplexer: BrowserMultiplexer, launch_id: str, browser_command: Sequence[str], relay_command: Sequence[str] | None
) -> BrowserWindowHandle:
    try:
        match multiplexer:
            case "tmux":
                return open_tmux_browser_windows(launch_id=launch_id, browser_command=browser_command, relay_command=relay_command)
            case "tuios":
                return open_tuios_browser_windows(launch_id=launch_id, browser_command=browser_command, relay_command=relay_command)
            case "zellij":
                return open_zellij_browser_windows(launch_id=launch_id, browser_command=browser_command, relay_command=relay_command)
    except ValueError as error:
        raise RuntimeError(str(error)) from error


def open_relay_window(*, handle: BrowserWindowHandle, launch_id: str, relay_command: Sequence[str]) -> BrowserWindowHandle:
    try:
        match handle.multiplexer:
            case "tmux":
                return open_tmux_relay_window(handle=handle, launch_id=launch_id, relay_command=relay_command)
            case "tuios":
                return open_tuios_relay_window(handle=handle, launch_id=launch_id, relay_command=relay_command)
            case "zellij":
                return open_zellij_relay_window(handle=handle, launch_id=launch_id, relay_command=relay_command)
    except ValueError as error:
        raise RuntimeError(str(error)) from error


def close_browser_windows(*, handle: BrowserWindowHandle) -> None:
    try:
        match handle.multiplexer:
            case "tmux":
                close_tmux_browser_windows(handle=handle)
            case "tuios":
                close_tuios_browser_windows(handle=handle)
            case "zellij":
                close_zellij_browser_windows(handle=handle)
    except ValueError as error:
        raise RuntimeError(str(error)) from error


def attach_browser_windows(*, handle: BrowserWindowHandle) -> None:
    if platform.system() == "Windows":
        attach_command = ("pwsh", "-NoLogo", "-NoProfile", "-Command", handle.attach_script)
    else:
        attach_command = ("bash", "-c", handle.attach_script)
    result = subprocess.run(attach_command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{handle.multiplexer} attach failed with exit code {result.returncode}: {handle.attach_script}")
