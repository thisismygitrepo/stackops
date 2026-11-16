from dataclasses import dataclass
from pathlib import Path
from typing import cast, get_args

import psutil

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_CDP_RELAY_MODULE, BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    browser_executable_names,
    command_has_option,
    command_option_value,
    normalize_executable_name,
)


@dataclass(frozen=True)
class OpenBrowserProcess:
    browser: BrowserName
    process_id: int
    profile_path: Path | None
    debugging_port: int | None
    started_at: float


def find_relay_process_id(*, listen_port: int) -> int | None:
    for process in psutil.process_iter():
        try:
            command = tuple(process.cmdline())
            if BROWSER_CDP_RELAY_MODULE in command and command_has_option(command=command, name="--listen-port", value=str(listen_port)):
                return process.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def collect_open_browsers() -> tuple[OpenBrowserProcess, ...]:
    browsers = cast(tuple[BrowserName, ...], get_args(BrowserName))
    executable_names_by_browser: dict[BrowserName, set[str]] = {browser: browser_executable_names(browser=browser) for browser in browsers}
    open_browsers: list[OpenBrowserProcess] = []
    for process in psutil.process_iter():
        try:
            command = tuple(process.cmdline())
            if not command or process.status() == psutil.STATUS_ZOMBIE:
                continue
            if any(argument.startswith("--type=") or argument == "-contentproc" for argument in command):
                continue
            executable_name = normalize_executable_name(executable_name=command[0])
            browser: BrowserName | None = next((candidate for candidate in browsers if executable_name in executable_names_by_browser[candidate]), None)
            if browser is None:
                continue
            profile_option = "--profile" if browser == "firefox" else "--user-data-dir"
            port_option = "--port" if browser == "safari" else "--remote-debugging-port"
            profile_value = command_option_value(command=command, name=profile_option)
            port_value = command_option_value(command=command, name=port_option)
            open_browsers.append(
                OpenBrowserProcess(
                    browser=browser,
                    process_id=process.pid,
                    profile_path=None if profile_value is None else Path(profile_value),
                    debugging_port=int(port_value) if port_value is not None and port_value.isdigit() else None,
                    started_at=process.create_time(),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return tuple(sorted(open_browsers, key=lambda open_browser: (open_browser.browser, open_browser.started_at)))
