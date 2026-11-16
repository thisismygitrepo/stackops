from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    REMOTE_DEBUGGING_LAN,
    REMOTE_DEBUGGING_LOCALHOST,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_launch import repair_detached_browser_relay
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    RunningBrowserProcess,
    find_running_browser_processes,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_details import build_browser_launch_details
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    ExistingBrowserLaunchResult,
    build_existing_launch_result,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import (
    assert_tcp_port_available,
    build_relay_command,
    ensure_cdp_page_target,
    tcp_port_is_open,
    verify_cdp_endpoint,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import collect_browser_launch_status
from stackops.scripts.python.helpers.helpers_agents.agents_browser_multiplexed_launch import repair_multiplexed_browser_relay
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def reuse_browser_launch_if_active(
    *,
    browser: BrowserName,
    browser_path: Path,
    profile_path: Path | None,
    port: int,
    lan: bool,
) -> ExistingBrowserLaunchResult | None:
    launcher = get_browser_launcher(browser=browser)
    for status in collect_browser_launch_status():
        launch = status.launch
        if status.browser_process_id is None:
            continue
        if launch.browser != browser or launch.profile_path != profile_path or launch.port != port or launch.relay_expected != lan:
            continue
        if not tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=launch.browser_port):
            continue
        details = build_browser_launch_details(
            browser=browser,
            browser_path=browser_path,
            profile_path=profile_path,
            port=port,
            browser_port=launch.browser_port,
            lan=lan,
        )
        repaired_relay = False
        if launch.relay_expected and (not status.relay_running or not tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=launch.port)):
            assert_tcp_port_available(host=REMOTE_DEBUGGING_LAN, port=launch.port)
            relay_command = build_relay_command(listen_port=launch.port, target_port=launch.browser_port)
            if launch.windows is None:
                repair_detached_browser_relay(
                    details=details,
                    browser_process_id=launch.process_id,
                    browser_process_created_at=launch.process_created_at,
                )
            else:
                repair_multiplexed_browser_relay(
                    details=details,
                    windows=launch.windows,
                    launch_id=launch.launch_id,
                    browser_process_id=launch.process_id,
                    browser_process_created_at=launch.process_created_at,
                    relay_command=relay_command,
                )
            if launcher.endpoint_protocol == "cdp":
                verify_cdp_endpoint(port=launch.port)
            repaired_relay = True
        opened_page = ensure_cdp_page_target(port=launch.browser_port) if launcher.endpoint_protocol == "cdp" else False
        return build_existing_launch_result(
            details=details,
            process_id=status.browser_process_id,
            owner="detached" if launch.windows is None else launch.windows.multiplexer,
            opened_page=opened_page,
            repaired_relay=repaired_relay,
        )

    if profile_path is None:
        return None

    for running_process in find_running_browser_processes(browser=browser, profile_path=profile_path):
        if not lan and running_process.browser_port == port and tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=port):
            details = build_browser_launch_details(
                browser=browser,
                browser_path=browser_path,
                profile_path=profile_path,
                port=port,
                browser_port=port,
                lan=False,
            )
            return build_existing_launch_result(
                details=details,
                process_id=running_process.process_id,
                owner="external",
                opened_page=ensure_cdp_page_target(port=port) if launcher.endpoint_protocol == "cdp" else False,
                repaired_relay=False,
            )
        _raise_profile_conflict(
            browser=browser,
            profile_path=profile_path,
            port=port,
            lan=lan,
            running_process=running_process,
        )
    return None


def _raise_profile_conflict(
    *,
    browser: BrowserName,
    profile_path: Path,
    port: int,
    lan: bool,
    running_process: RunningBrowserProcess,
) -> None:
    requested_host = REMOTE_DEBUGGING_LAN if lan else REMOTE_DEBUGGING_LOCALHOST
    raise RuntimeError(
        f"{browser} profile {profile_path} is already in use by PID {running_process.process_id} "
        f"on browser port {running_process.browser_port}; cannot launch it again on {requested_host}:{port}"
    )
