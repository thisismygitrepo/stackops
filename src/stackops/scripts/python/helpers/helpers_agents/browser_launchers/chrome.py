from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.browser_launchers.common import require_profile_path, windows_app_paths
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.models import BrowserLauncher


def known_paths(*, system_name: str) -> tuple[Path, ...]:
    match system_name:
        case "Windows":
            return windows_app_paths(relative_parts=("Google", "Chrome", "Application", "chrome.exe"))
        case "Darwin":
            return (
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path.home().joinpath("Applications", "Google Chrome.app", "Contents", "MacOS", "Google Chrome"),
            )
        case _:
            return ()


def build_command(*, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]:
    required_profile_path = require_profile_path(browser="chrome", profile_path=profile_path)
    return (
        str(browser_path),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={required_profile_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    )


LAUNCHER = BrowserLauncher(
    browser="chrome",
    display_name="Chrome",
    command_names=("google-chrome-stable", "google-chrome", "chrome", "chrome.exe"),
    known_paths=known_paths,
    build_command=build_command,
    endpoint_protocol="cdp",
    endpoint_label="Chrome DevTools Protocol",
    endpoint_short_label="CDP",
    process_label="Chrome",
    profile_mode="stackops-profile",
    setup_note=None,
)
