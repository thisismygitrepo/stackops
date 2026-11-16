from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName, BrowserRuntime
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_launch import launch_detached_browser
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_details import build_browser_launch_details
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock import browser_launch_lock
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchResult
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import build_relay_command, resolve_browser_endpoint_port
from stackops.scripts.python.helpers.helpers_agents.agents_browser_lifecycle import prepare_browser_launch_state
from stackops.scripts.python.helpers.helpers_agents.agents_browser_multiplexed_launch import launch_multiplexed_browser
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_filesystem import remove_owned_profile_directories
from stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution import resolve_browser_executable, resolve_profile_path, validate_port
from stackops.scripts.python.helpers.helpers_agents.agents_browser_reuse import reuse_browser_launch_if_active
from stackops.scripts.python.helpers.helpers_agents.agents_browser_temporary_profiles import copy_browser_profile_to_temporary


def launch_browser(
    *, browser: BrowserName, port: int, profile_name: str | None, temporary: bool, lan: bool, runtime: BrowserRuntime
) -> BrowserLaunchResult:
    validate_port(port=port)
    if temporary and profile_name is None:
        raise ValueError("--tmp requires --profile")
    with browser_launch_lock():
        profile_path = resolve_profile_path(browser=browser, profile_name=profile_name, port=port)
        browser_path = resolve_browser_executable(browser=browser)
        prepare_browser_launch_state()
        temporary_profile_path: Path | None = None
        if temporary:
            if profile_path is None:
                raise RuntimeError("The selected browser did not resolve a profile path for --tmp")
            temporary_profile_path = copy_browser_profile_to_temporary(browser=browser, source_path=profile_path)
            profile_path = temporary_profile_path
        elif profile_path is not None:
            profile_path.mkdir(parents=True, exist_ok=True)

        runtime_launch_attempted = False
        try:
            existing_launch = reuse_browser_launch_if_active(
                browser=browser, browser_path=browser_path, profile_path=profile_path, port=port, lan=lan
            )
            if existing_launch is not None:
                return existing_launch

            browser_port = resolve_browser_endpoint_port(exposed_port=port, lan=lan)
            details = build_browser_launch_details(
                browser=browser, browser_path=browser_path, profile_path=profile_path, port=port, browser_port=browser_port, lan=lan
            )
            relay_command = build_relay_command(listen_port=port, target_port=browser_port) if lan else None
            runtime_launch_attempted = True
            match runtime:
                case "detached":
                    return launch_detached_browser(details=details, lan=lan)
                case "tmux" | "tuios" | "zellij":
                    return launch_multiplexed_browser(multiplexer=runtime, details=details, relay_command=relay_command)
        except BaseException as error:
            if temporary_profile_path is not None and not runtime_launch_attempted:
                cleanup_failures = remove_owned_profile_directories(directories=(temporary_profile_path,))
                for cleanup_failure in cleanup_failures:
                    error.add_note(f"Temporary browser profile cleanup failed: {cleanup_failure}")
            raise
