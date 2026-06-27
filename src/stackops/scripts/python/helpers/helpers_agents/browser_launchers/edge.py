from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.browser_launchers.common import require_profile_path, windows_app_paths
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.models import BrowserLauncher


def known_paths(*, system_name: str) -> tuple[Path, ...]:
    match system_name:
        case "Windows":
            return windows_app_paths(relative_parts=("Microsoft", "Edge", "Application", "msedge.exe"))
        case "Darwin":
            return (
                Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path.home().joinpath("Applications", "Microsoft Edge.app", "Contents", "MacOS", "Microsoft Edge"),
            )
        case _:
            return ()


def build_command(*, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]:
    required_profile_path = require_profile_path(browser="edge", profile_path=profile_path)
    return (
        str(browser_path),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={required_profile_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    )


LAUNCHER = BrowserLauncher(
    browser="edge",
    display_name="Edge",
    command_names=("microsoft-edge-stable", "microsoft-edge", "msedge", "msedge.exe"),
    known_paths=known_paths,
    build_command=build_command,
    endpoint_protocol="cdp",
    endpoint_label="Chrome DevTools Protocol",
    endpoint_short_label="CDP",
    process_label="Edge",
    profile_mode="stackops-profile",
    setup_note=None,
)
