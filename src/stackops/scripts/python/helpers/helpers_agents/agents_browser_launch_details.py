from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    AGENT_BROWSER_ROOT,
    REMOTE_DEBUGGING_LAN,
    REMOTE_DEBUGGING_LOCALHOST,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchDetails
from stackops.scripts.python.helpers.helpers_agents.agents_browser_prompt import write_browser_prompt
from stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution import build_browser_launch_command
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def build_browser_launch_details(
    *,
    browser: BrowserName,
    browser_path: Path,
    profile_path: Path | None,
    port: int,
    browser_port: int,
    lan: bool,
) -> BrowserLaunchDetails:
    launcher = get_browser_launcher(browser=browser)
    host = REMOTE_DEBUGGING_LAN if lan else REMOTE_DEBUGGING_LOCALHOST
    command = build_browser_launch_command(
        browser=browser,
        browser_path=browser_path,
        port=browser_port,
        profile_path=profile_path,
    )
    prompt_path = write_browser_prompt(
        agent_browser_root=AGENT_BROWSER_ROOT,
        browser=browser,
        port=port,
        browser_port=browser_port,
        host=host,
        lan=lan,
        profile_path=profile_path,
    )
    return BrowserLaunchDetails(
        browser=browser,
        browser_path=browser_path,
        command=command,
        endpoint_label=launcher.endpoint_label,
        endpoint_short_label=launcher.endpoint_short_label,
        process_label=launcher.process_label,
        host=host,
        port=port,
        browser_port=browser_port,
        profile_path=profile_path,
        prompt_path=prompt_path,
    )
