from dataclasses import dataclass
from datetime import datetime

from rich import box
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppWindow, BrowserWindowsUnavailable
from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_windows import collect_browser_windows
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName, BrowserRuntime
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import BrowserLaunchStatus, collect_browser_launch_status
from stackops.scripts.python.helpers.helpers_agents.agents_browser_process_scan import OpenBrowserProcess, collect_open_browsers


@dataclass(frozen=True)
class OpenBrowserStatus:
    browser: OpenBrowserProcess
    launch_id: str | None
    runtime: BrowserRuntime | None
    browser_windows: tuple[BrowserAppWindow, ...] | BrowserWindowsUnavailable


@dataclass(frozen=True)
class BrowserLaunchWindowsStatus(BrowserLaunchStatus):
    browser_windows: tuple[BrowserAppWindow, ...] | BrowserWindowsUnavailable


def collect_open_browser_status(*, browser: BrowserName | None) -> tuple[OpenBrowserStatus, ...]:
    launches_by_process_id = {status.browser_process_id: status.launch for status in collect_browser_launch_status() if status.browser_process_id is not None}
    rows: list[OpenBrowserStatus] = []
    for open_browser in collect_open_browsers():
        if browser is not None and open_browser.browser != browser:
            continue
        launch = launches_by_process_id.get(open_browser.process_id)
        rows.append(
            OpenBrowserStatus(
                browser=open_browser,
                launch_id=None if launch is None else launch.launch_id,
                runtime=None if launch is None else "detached" if launch.windows is None else launch.windows.multiplexer,
                browser_windows=collect_browser_windows(browser=open_browser.browser, port=open_browser.debugging_port),
            )
        )
    return tuple(rows)


def collect_browser_launch_windows_status(*, browser: BrowserName | None) -> tuple[BrowserLaunchWindowsStatus, ...]:
    return tuple(
        BrowserLaunchWindowsStatus(
            launch=status.launch,
            state=status.state,
            browser_process_id=status.browser_process_id,
            relay_running=status.relay_running,
            browser_windows=BrowserWindowsUnavailable(reason="no_endpoint")
            if status.browser_process_id is None
            else collect_browser_windows(browser=status.launch.browser, port=status.launch.browser_port),
        )
        for status in collect_browser_launch_status()
        if browser is None or status.launch.browser == browser
    )


def show_browser_launch_status(*, statuses: tuple[BrowserLaunchWindowsStatus, ...]) -> None:
    table = Table(title=f"StackOps browser launches: {len(statuses)} tracked", box=box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("Launch", overflow="fold")
    table.add_column("Runtime")
    table.add_column("Browser")
    table.add_column("Profile", overflow="fold")
    table.add_column("Endpoint")
    table.add_column("State")
    table.add_column("Browser PID", justify="right")
    table.add_column("Relay PID", justify="right")
    table.add_column("Session", overflow="fold")
    table.add_column("Windows")
    for status in statuses:
        table.add_row(*_launch_row(status=status))
    Console().print(table)


def show_open_browser_status(*, rows: tuple[OpenBrowserStatus, ...]) -> None:
    managed_count = sum(1 for row in rows if row.launch_id is not None)
    table = Table(
        title=f"Open browsers: {len(rows)} running, {managed_count} launched by StackOps", box=box.SIMPLE_HEAVY, show_lines=False
    )
    table.add_column("Browser")
    table.add_column("PID", justify="right")
    table.add_column("Debug port", justify="right")
    table.add_column("Profile", overflow="fold")
    table.add_column("Started")
    table.add_column("Owner", overflow="fold")
    table.add_column("Windows")
    for row in rows:
        owner = "external" if row.launch_id is None else f"{row.runtime} · {row.launch_id}"
        table.add_row(
            row.browser.browser,
            str(row.browser.process_id),
            "-" if row.browser.debugging_port is None else str(row.browser.debugging_port),
            "default" if row.browser.profile_path is None else str(row.browser.profile_path),
            datetime.fromtimestamp(row.browser.started_at).strftime("%Y-%m-%d %H:%M"),
            owner,
            _windows_cell(browser_windows=row.browser_windows),
        )
    Console().print(table)


def _windows_cell(*, browser_windows: tuple[BrowserAppWindow, ...] | BrowserWindowsUnavailable) -> str:
    match browser_windows:
        case BrowserWindowsUnavailable(reason="session_in_use"):
            return "session in use"
        case BrowserWindowsUnavailable():
            return "-"
        case ():
            return "none"
        case _:
            return "\n".join(
                f"{window.window_id} · {len(window.tabs)} {'tab' if len(window.tabs) == 1 else 'tabs'} · {window.state}" for window in browser_windows
            )


def _launch_row(*, status: BrowserLaunchWindowsStatus) -> tuple[str, ...]:
    launch = status.launch
    endpoint = f"{launch.host}:{launch.port}"
    if launch.relay_expected:
        endpoint = f"{endpoint} -> 127.0.0.1:{launch.browser_port}"
    relay_process = "-"
    if launch.relay_expected and launch.relay_process_id is None:
        relay_process = "not started"
    elif launch.relay_process_id is not None:
        relay_process = str(launch.relay_process_id) if status.relay_running else f"{launch.relay_process_id} (stopped)"
    return (
        launch.launch_id,
        "detached" if launch.windows is None else launch.windows.multiplexer,
        launch.browser,
        launch.profile,
        endpoint,
        status.state,
        str(status.browser_process_id) if status.browser_process_id is not None else f"{launch.process_id} (stopped)",
        relay_process,
        "-" if launch.windows is None else launch.windows.session_name,
        _windows_cell(browser_windows=status.browser_windows),
    )
