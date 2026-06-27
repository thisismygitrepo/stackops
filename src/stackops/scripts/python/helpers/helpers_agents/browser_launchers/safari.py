from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.browser_launchers.models import BrowserLauncher


def known_paths(*, system_name: str) -> tuple[Path, ...]:
    match system_name:
        case "Darwin":
            return (Path("/usr/bin/safaridriver"),)
        case _:
            return ()


def build_command(*, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]:
    if profile_path is not None:
        raise RuntimeError("safari does not support StackOps browser profiles")
    return (str(browser_path), "--port", str(port))


LAUNCHER = BrowserLauncher(
    browser="safari",
    display_name="Safari",
    command_names=("safaridriver",),
    known_paths=known_paths,
    build_command=build_command,
    endpoint_protocol="webdriver",
    endpoint_label="WebDriver",
    endpoint_short_label="WebDriver",
    process_label="safaridriver",
    profile_mode="unsupported",
    setup_note="Run `safaridriver --enable` once before first Safari WebDriver use.",
)
