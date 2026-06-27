import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName


def windows_app_paths(*, relative_parts: tuple[str, ...]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for environment_variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        environment_value = os.environ.get(environment_variable)
        if environment_value is not None and environment_value.strip() != "":
            paths.append(Path(environment_value).joinpath(*relative_parts))
    return tuple(paths)


def require_profile_path(*, browser: BrowserName, profile_path: Path | None) -> Path:
    if profile_path is None:
        raise RuntimeError(f"""{browser} launcher requires a StackOps profile path""")
    return profile_path
