from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.browser_launchers.common import require_profile_path, windows_app_paths
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.models import BrowserLauncher


def known_paths(*, system_name: str) -> tuple[Path, ...]:
    match system_name:
        case "Windows":
            return windows_app_paths(relative_parts=("BraveSoftware", "Brave-Browser", "Application", "brave.exe"))
        case "Darwin":
            return (
                Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
                Path.home().joinpath("Applications", "Brave Browser.app", "Contents", "MacOS", "Brave Browser"),
            )
        case _:
            return ()


def build_command(*, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]:
    required_profile_path = require_profile_path(browser="brave", profile_path=profile_path)
    return (
        str(browser_path),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={required_profile_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    )


LAUNCHER = BrowserLauncher(
    browser="brave",
    display_name="Brave",
    command_names=("brave-browser", "brave-browser-stable", "brave", "brave.exe"),
    known_paths=known_paths,
    build_command=build_command,
    endpoint_protocol="cdp",
    endpoint_label="Chrome DevTools Protocol",
    endpoint_short_label="CDP",
    process_label="Brave",
    profile_mode="stackops-profile",
    setup_note=None,
)
