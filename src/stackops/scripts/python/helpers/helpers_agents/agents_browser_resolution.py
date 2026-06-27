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
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def validate_port(*, port: int) -> None:
    if port < 1 or port > 65535:
        raise ValueError("--port must be between 1 and 65535")


def resolve_browser_executable(*, browser: BrowserName) -> Path:
    system_name = platform.system()
    launcher = get_browser_launcher(browser=browser)
    candidates = _dedupe_paths(paths=(*launcher.known_paths(system_name=system_name), *_paths_from_names(names=launcher.command_names)))
    for candidate in candidates:
        if _is_executable_file(path=candidate, system_name=system_name):
            return candidate.expanduser()
    searched = "\n".join(str(candidate) for candidate in candidates)
    raise RuntimeError(f"""Could not find {launcher.process_label} executable for {system_name}. Searched:\n{searched}""")


def resolve_profile_path(*, browser: BrowserName, profile_name: str | None, port: int) -> Path | None:
    launcher = get_browser_launcher(browser=browser)
    if launcher.profile_mode == "unsupported":
        if profile_name is not None:
            raise ValueError(f"""{launcher.display_name} does not support --profile""")
        return None
    if profile_name is None:
        return TEMP_BROWSER_PROFILES_ROOT.expanduser().joinpath(browser, f"port-{port}")
    normalized_profile_name = _normalize_profile_name(profile_name=profile_name)
    return BROWSER_PROFILES_ROOT.expanduser().joinpath(browser, normalized_profile_name)


def build_browser_launch_command(*, browser: BrowserName, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]:
    launcher = get_browser_launcher(browser=browser)
    return launcher.build_command(browser_path=browser_path, port=port, profile_path=profile_path)


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
