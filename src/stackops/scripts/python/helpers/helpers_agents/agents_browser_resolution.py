from collections.abc import Sequence
import os
from pathlib import Path
import platform
import shutil

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_PROFILES_ROOT,
    BrowserName,
    TEMP_BROWSER_PROFILES_ROOT,
)


def validate_port(*, port: int) -> None:
    if port < 1 or port > 65535:
        raise ValueError("--port must be between 1 and 65535")


def resolve_browser_executable(*, browser: BrowserName) -> Path:
    system_name = platform.system()
    candidates = _dedupe_paths(paths=(*_known_browser_paths(browser=browser, system_name=system_name), *_paths_from_names(names=_browser_command_names(browser=browser))))
    for candidate in candidates:
        if _is_executable_file(path=candidate, system_name=system_name):
            return candidate.expanduser()
    searched = "\n".join(str(candidate) for candidate in candidates)
    raise ValueError(f"""Could not find {browser} executable for {system_name}. Searched:\n{searched}""")


def resolve_profile_path(*, browser: BrowserName, profile_name: str | None, port: int) -> Path:
    if profile_name is None:
        return TEMP_BROWSER_PROFILES_ROOT.expanduser().joinpath(browser, f"port-{port}")
    normalized_profile_name = _normalize_profile_name(profile_name=profile_name)
    return BROWSER_PROFILES_ROOT.expanduser().joinpath(browser, normalized_profile_name)


def build_browser_launch_command(*, browser_path: Path, port: int, host: str, profile_path: Path) -> tuple[str, ...]:
    return (
        str(browser_path),
        f"--remote-debugging-port={port}",
        f"--remote-debugging-address={host}",
        f"--user-data-dir={profile_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-allow-origins=*",
        "about:blank",
    )


def _normalize_profile_name(*, profile_name: str) -> str:
    normalized_profile_name = profile_name.strip()
    invalid_characters = ("/", "\\", ":", "*", "?", '"', "<", ">", "|")
    if normalized_profile_name == "":
        raise ValueError("--profile must not be empty when provided")
    if normalized_profile_name in {".", ".."}:
        raise ValueError("--profile must be a profile name, not a path")
    if any(invalid_character in normalized_profile_name for invalid_character in invalid_characters):
        raise ValueError("--profile must be a single profile name without path separators or filesystem-reserved characters")
    if Path(normalized_profile_name).is_absolute():
        raise ValueError("--profile must be a profile name, not an absolute path")
    return normalized_profile_name


def _browser_command_names(*, browser: BrowserName) -> tuple[str, ...]:
    match browser:
        case "chrome":
            return ("google-chrome-stable", "google-chrome", "chrome", "chrome.exe")
        case "brave":
            return ("brave-browser", "brave-browser-stable", "brave", "brave.exe")


def _known_browser_paths(*, browser: BrowserName, system_name: str) -> tuple[Path, ...]:
    match (system_name, browser):
        case ("Windows", "chrome"):
            return _windows_app_paths(relative_parts=("Google", "Chrome", "Application", "chrome.exe"))
        case ("Windows", "brave"):
            return _windows_app_paths(relative_parts=("BraveSoftware", "Brave-Browser", "Application", "brave.exe"))
        case ("Darwin", "chrome"):
            return (
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path.home().joinpath("Applications", "Google Chrome.app", "Contents", "MacOS", "Google Chrome"),
            )
        case ("Darwin", "brave"):
            return (
                Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
                Path.home().joinpath("Applications", "Brave Browser.app", "Contents", "MacOS", "Brave Browser"),
            )
        case _:
            return ()


def _windows_app_paths(*, relative_parts: tuple[str, ...]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for environment_variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        environment_value = os.environ.get(environment_variable)
        if environment_value is not None and environment_value.strip() != "":
            paths.append(Path(environment_value).joinpath(*relative_parts))
    return tuple(paths)


def _paths_from_names(*, names: Sequence[str]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for name in names:
        located = shutil.which(name)
        if located is not None:
            paths.append(Path(located))
    return tuple(paths)


def _dedupe_paths(*, paths: Sequence[Path]) -> tuple[Path, ...]:
    seen: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        expanded_path = path.expanduser()
        key = os.path.normcase(str(expanded_path))
        if key not in seen:
            seen.add(key)
            unique_paths.append(expanded_path)
    return tuple(unique_paths)


def _is_executable_file(*, path: Path, system_name: str) -> bool:
    expanded_path = path.expanduser()
    if not expanded_path.is_file():
        return False
    if system_name == "Windows":
        return True
    return os.access(expanded_path, os.X_OK)
