import time

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS,
    BROWSER_RELAY_PROCESS_LABEL,
    REMOTE_DEBUGGING_LOCALHOST,
    BrowserMultiplexer,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    process_created_at,
    registered_process_is_running,
    scan_browser_process_id,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts import close_browser_windows, open_browser_windows, open_relay_window
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    BrowserLaunchDetails,
    BrowserWindowHandle,
    NewBrowserLaunchResult,
    build_new_launch_result,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import prepare_browser_launch_registry, record_browser_launch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import verify_cdp_endpoint, wait_for_tcp_endpoint
from stackops.scripts.python.helpers.helpers_agents.agents_browser_process_scan import find_relay_process_id
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def launch_multiplexed_browser(
    *, multiplexer: BrowserMultiplexer, details: BrowserLaunchDetails, relay_command: tuple[str, ...] | None
) -> NewBrowserLaunchResult:
    prepare_browser_launch_registry()
    launch_id = browser_launch_id(browser=details.browser, profile_path=details.profile_path, port=details.port)
    windows = open_browser_windows(multiplexer=multiplexer, launch_id=launch_id, browser_command=details.command, relay_command=relay_command)
    try:
        wait_for_tcp_endpoint(host=REMOTE_DEBUGGING_LOCALHOST, port=details.browser_port, process=None, process_label=details.process_label)
        if get_browser_launcher(browser=details.browser).endpoint_protocol == "cdp":
            verify_cdp_endpoint(port=details.browser_port)
        browser_process_id = scan_browser_process_id(browser=details.browser, browser_port=details.browser_port, profile_path=details.profile_path)
        if browser_process_id is None:
            raise RuntimeError(f"{details.process_label} answered on port {details.browser_port}, but its process could not be found")
        browser_created_at = process_created_at(process_id=browser_process_id, process_label=details.process_label)
        relay_process_id: int | None = None
        relay_created_at: float | None = None
        if relay_command is not None:
            relay_process_id, relay_created_at = _confirm_relay(details=details)
        time.sleep(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
        if not registered_process_is_running(process_id=browser_process_id, process_created_at=browser_created_at):
            raise RuntimeError(f"{details.process_label} exited while its {multiplexer} window became ready")
        if (
            relay_process_id is not None
            and relay_created_at is not None
            and not registered_process_is_running(process_id=relay_process_id, process_created_at=relay_created_at)
        ):
            raise RuntimeError(f"{BROWSER_RELAY_PROCESS_LABEL} exited while its {multiplexer} window became ready")
        record_browser_launch(
            details=details,
            process_id=browser_process_id,
            process_created_at=browser_created_at,
            relay_expected=relay_command is not None,
            relay_process_id=relay_process_id,
            relay_process_created_at=relay_created_at,
            windows=windows,
        )
    except BaseException:
        close_browser_windows(handle=windows)
        raise
    return build_new_launch_result(details=details, process_id=browser_process_id, relay_process_id=relay_process_id, windows=windows)


def repair_multiplexed_browser_relay(
    *,
    details: BrowserLaunchDetails,
    windows: BrowserWindowHandle,
    launch_id: str,
    browser_process_id: int,
    browser_process_created_at: float,
    relay_command: tuple[str, ...],
) -> None:
    repaired_windows = open_relay_window(handle=windows, launch_id=launch_id, relay_command=relay_command)
    try:
        relay_process_id, relay_created_at = _confirm_relay(details=details)
        record_browser_launch(
            details=details,
            process_id=browser_process_id,
            process_created_at=browser_process_created_at,
            relay_expected=True,
            relay_process_id=relay_process_id,
            relay_process_created_at=relay_created_at,
            windows=repaired_windows,
        )
    except BaseException:
        close_browser_windows(
            handle=BrowserWindowHandle(
                multiplexer=repaired_windows.multiplexer,
                session_name=repaired_windows.session_name,
                targets=repaired_windows.targets[len(windows.targets) :],
                attach_script=repaired_windows.attach_script,
            )
        )
        raise


def _confirm_relay(*, details: BrowserLaunchDetails) -> tuple[int, float]:
    wait_for_tcp_endpoint(host=REMOTE_DEBUGGING_LOCALHOST, port=details.port, process=None, process_label=BROWSER_RELAY_PROCESS_LABEL)
    relay_process_id = find_relay_process_id(listen_port=details.port)
    if relay_process_id is None:
        raise RuntimeError(f"{BROWSER_RELAY_PROCESS_LABEL} answered on port {details.port}, but its process could not be found")
    relay_created_at = process_created_at(process_id=relay_process_id, process_label=BROWSER_RELAY_PROCESS_LABEL)
    if get_browser_launcher(browser=details.browser).endpoint_protocol == "cdp":
        verify_cdp_endpoint(port=details.port)
    return relay_process_id, relay_created_at
