import os

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import REMOTE_DEBUGGING_LOCALHOST
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import process_created_at
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    BrowserLaunchDetails,
    NewBrowserLaunchResult,
    build_new_launch_result,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import prepare_browser_launch_registry, record_browser_launch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import (
    start_browser_process,
    start_endpoint_relay,
    terminate_background_process,
    verify_cdp_endpoint,
    wait_for_tcp_endpoint,
)
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def launch_detached_browser(*, details: BrowserLaunchDetails, lan: bool) -> NewBrowserLaunchResult:
    prepare_browser_launch_registry()
    browser_process = start_browser_process(
        command=details.command,
        process_label=details.process_label,
        environment=os.environ,
    )
    relay_process = None
    try:
        wait_for_tcp_endpoint(
            host=REMOTE_DEBUGGING_LOCALHOST,
            port=details.browser_port,
            process=browser_process,
            process_label=details.process_label,
        )
        if get_browser_launcher(browser=details.browser).endpoint_protocol == "cdp":
            verify_cdp_endpoint(port=details.browser_port)
        browser_created_at = process_created_at(process_id=browser_process.pid, process_label=details.process_label)
        if lan:
            relay_process = start_endpoint_relay(
                listen_port=details.port,
                target_port=details.browser_port,
            )
            wait_for_tcp_endpoint(
                host=REMOTE_DEBUGGING_LOCALHOST,
                port=details.port,
                process=relay_process,
                process_label="browser endpoint LAN relay",
            )
            if get_browser_launcher(browser=details.browser).endpoint_protocol == "cdp":
                verify_cdp_endpoint(port=details.port)
        relay_process_id = None if relay_process is None else relay_process.pid
        relay_created_at = (
            None
            if relay_process is None
            else process_created_at(process_id=relay_process.pid, process_label="browser endpoint LAN relay")
        )
        record_browser_launch(
            details=details,
            process_id=browser_process.pid,
            process_created_at=browser_created_at,
            relay_expected=lan,
            relay_process_id=relay_process_id,
            relay_process_created_at=relay_created_at,
            windows=None,
        )
        return build_new_launch_result(details=details, process_id=browser_process.pid, relay_process_id=relay_process_id, windows=None)
    except RuntimeError:
        if relay_process is not None:
            terminate_background_process(process=relay_process, process_label="browser endpoint LAN relay")
        terminate_background_process(process=browser_process, process_label=details.process_label)
        raise


def repair_detached_browser_relay(
    *,
    details: BrowserLaunchDetails,
    browser_process_id: int,
    browser_process_created_at: float,
) -> int:
    relay_process = start_endpoint_relay(
        listen_port=details.port,
        target_port=details.browser_port,
    )
    try:
        wait_for_tcp_endpoint(
            host=REMOTE_DEBUGGING_LOCALHOST,
            port=details.port,
            process=relay_process,
            process_label="browser endpoint LAN relay",
        )
        if get_browser_launcher(browser=details.browser).endpoint_protocol == "cdp":
            verify_cdp_endpoint(port=details.port)
        relay_created_at = process_created_at(
            process_id=relay_process.pid,
            process_label="browser endpoint LAN relay",
        )
        record_browser_launch(
            details=details,
            process_id=browser_process_id,
            process_created_at=browser_process_created_at,
            relay_expected=True,
            relay_process_id=relay_process.pid,
            relay_process_created_at=relay_created_at,
            windows=None,
        )
        return relay_process.pid
    except RuntimeError:
        terminate_background_process(process=relay_process, process_label="browser endpoint LAN relay")
        raise
