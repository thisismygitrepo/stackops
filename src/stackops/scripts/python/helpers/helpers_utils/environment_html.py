import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, TypedDict

from stackops.scripts.python.helpers.helpers_env.path_manager_backend import get_path_entries
from stackops.utils.html_report import show_html_report


_SENSITIVE_NAME: Final[re.Pattern[str]] = re.compile(
    r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|COOKIE|PRIVATE|AUTH|(?:^|_)PAT(?:_|$)", flags=re.IGNORECASE
)
_CREDENTIAL_URL: Final[re.Pattern[str]] = re.compile(r"://[^/\s:@]+:[^/\s@]+@")


class EnvironmentHtmlVariable(TypedDict):
    name: str
    value: str | None


class EnvironmentHtmlPathEntry(TypedDict):
    path: str
    state: Literal["directory", "file", "missing", "unreadable"]
    commands: list[str]


class EnvironmentHtmlPayload(TypedDict):
    generated_at: str
    mode: Literal["variables", "path"]
    home_directory: str
    path_separator: str
    variables: list[EnvironmentHtmlVariable]
    path_entries: list[EnvironmentHtmlPathEntry]


def show_environment_html_report(*, which: Literal["PATH", "p", "ENV", "e"]) -> Path:
    variables: list[EnvironmentHtmlVariable] = []
    path_entries: list[EnvironmentHtmlPathEntry] = []
    mode: Literal["variables", "path"]
    if which in ("PATH", "p"):
        mode = "path"
        for path_entry in get_path_entries():
            directory = Path(path_entry)
            if not directory.exists():
                path_entries.append({"path": path_entry, "state": "missing", "commands": []})
            elif not directory.is_dir():
                path_entries.append({"path": path_entry, "state": "file", "commands": []})
            else:
                try:
                    commands = sorted(child.name for child in directory.iterdir() if child.is_file() and os.access(child, os.X_OK))
                    path_entries.append({"path": path_entry, "state": "directory", "commands": commands})
                except OSError:
                    path_entries.append({"path": path_entry, "state": "unreadable", "commands": []})
    else:
        mode = "variables"
        for name, value in sorted(os.environ.items(), key=lambda pair: pair[0].casefold()):
            hidden = _SENSITIVE_NAME.search(name) is not None or _CREDENTIAL_URL.search(value) is not None
            variables.append({"name": name, "value": None if hidden else value})
    payload: EnvironmentHtmlPayload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": mode,
        "home_directory": str(Path.home()),
        "path_separator": os.pathsep,
        "variables": variables,
        "path_entries": path_entries,
    }
    asset_directory = Path(__file__).with_name("environment_html_assets")
    return show_html_report(
        title="PATH entries" if mode == "path" else "Environment variables",
        payload_json=json.dumps(payload, ensure_ascii=False),
        style_path=asset_directory / "environment.css",
        script_paths=(
            asset_directory / "environment_data.js",
            asset_directory / "environment_variables.js",
            asset_directory / "environment_path.js",
            asset_directory / "environment_app.js",
        ),
        file_stem=f"environment_{mode}",
    )
