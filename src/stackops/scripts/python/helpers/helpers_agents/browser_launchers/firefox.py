from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.browser_launchers.common import require_profile_path, windows_app_paths
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.models import BrowserLauncher


def known_paths(*, system_name: str) -> tuple[Path, ...]:
    match system_name:
        case "Windows":
            return windows_app_paths(relative_parts=("Mozilla Firefox", "firefox.exe"))
        case "Darwin":
            return (
                Path("/Applications/Firefox.app/Contents/MacOS/firefox"),
                Path.home().joinpath("Applications", "Firefox.app", "Contents", "MacOS", "firefox"),
            )
        case _:
            return ()


def build_command(*, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]:
    required_profile_path = require_profile_path(browser="firefox", profile_path=profile_path)
    return (
        str(browser_path),
        "--remote-debugging-port",
        str(port),
        "--profile",
        str(required_profile_path),
        "--no-remote",
        "about:blank",
    )


LAUNCHER = BrowserLauncher(
    browser="firefox",
    display_name="Firefox",
    command_names=("firefox", "firefox-esr", "firefox-developer-edition", "firefox.exe"),
    known_paths=known_paths,
    build_command=build_command,
    endpoint_protocol="webdriver-bidi",
    endpoint_label="WebDriver BiDi",
    endpoint_short_label="WebDriver BiDi",
    process_label="Firefox",
    profile_mode="stackops-profile",
    setup_note=None,
)
