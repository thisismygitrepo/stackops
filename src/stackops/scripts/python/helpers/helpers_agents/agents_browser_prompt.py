from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BrowserName,
    REMOTE_DEBUGGING_LOCALHOST,
)
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def write_browser_prompt(
    *,
    browsing_root: Path,
    browser: BrowserName,
    port: int,
    browser_port: int,
    host: str,
    lan: bool,
    profile_path: Path | None,
) -> Path:
    launcher = get_browser_launcher(browser=browser)
    prompt_path = browsing_root.expanduser().joinpath("prompt.md")
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    lan_instructions = (
        f"""If this browser endpoint is on another computer, connect from the agent machine to `http://<LAN-IP>:{port}`.
StackOps is relaying {host}:{port} to {launcher.display_name}'s localhost-only {launcher.endpoint_label} endpoint at {REMOTE_DEBUGGING_LOCALHOST}:{browser_port}.
"""
        if lan
        else _build_local_connection_instructions(browser=browser, port=port)
    )
    profile_line = f"""Browser profile directory: {profile_path}
""" if profile_path is not None else ""
    setup_note = f"""
Setup note: {launcher.setup_note}
""" if launcher.setup_note is not None else ""
    workflow_text = _build_workflow_text(browser=browser, port=port, host=host)
    prompt_path.write_text(
        f"""I launched {launcher.display_name} with {launcher.endpoint_label} enabled on {host}:{port}.

{lan_instructions}
{setup_note}
{profile_line}
## Browser Automation

{workflow_text}
""",
        encoding="utf-8",
    )
    return prompt_path


def _build_local_connection_instructions(*, browser: BrowserName, port: int) -> str:
    launcher = get_browser_launcher(browser=browser)
    match launcher.endpoint_protocol:
        case "cdp":
            return f"""When working on this machine, connect agent-browser to this existing browser session with `--cdp {port}`.
"""
        case "webdriver-bidi" | "webdriver":
            return f"""When working on this machine, connect a {launcher.endpoint_label} client to `http://{REMOTE_DEBUGGING_LOCALHOST}:{port}`.
"""


def _build_workflow_text(*, browser: BrowserName, port: int, host: str) -> str:
    launcher = get_browser_launcher(browser=browser)
    match launcher.endpoint_protocol:
        case "cdp":
            return f"""Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:

1. `agent-browser open <url> --cdp {port}` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs like @e1 and @e2
3. `agent-browser click @e1` or `agent-browser fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
"""
        case "webdriver-bidi":
            return f"""Use a WebDriver BiDi client against `http://{host}:{port}`.

Core workflow:

1. Create a browser session with WebDriver BiDi enabled.
2. Navigate, inspect, and interact through the BiDi session.
3. Close the session when finished.
"""
        case "webdriver":
            return f"""Use a WebDriver client against `http://{host}:{port}`.

Core workflow:

1. Create a Safari WebDriver session.
2. Navigate, inspect, and interact through the WebDriver session.
3. Close the session when finished.
"""
