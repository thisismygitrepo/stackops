import json
import os
import re
from collections.abc import Mapping
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


# The variables of an environment by name, with the value left out where the name or the value looks like a secret.
# The HTML report and the web UI's Environment page both read through this, so one rule decides what is left out.
def read_environment_variables(*, environment: Mapping[str, str]) -> list[EnvironmentHtmlVariable]:
    variables: list[EnvironmentHtmlVariable] = []
    for name, value in sorted(environment.items(), key=lambda pair: pair[0].casefold()):
        hidden = _SENSITIVE_NAME.search(name) is not None or _CREDENTIAL_URL.search(value) is not None
        variables.append({"name": name, "value": None if hidden else value})
    return variables


# The folders of a program search path in lookup order, each with what it is and the programs it holds.
def read_path_entries(*, entries: list[str]) -> list[EnvironmentHtmlPathEntry]:
    path_entries: list[EnvironmentHtmlPathEntry] = []
    for path_entry in entries:
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
    return path_entries


def show_environment_html_report(*, which: Literal["PATH", "p", "ENV", "e"]) -> Path:
    variables: list[EnvironmentHtmlVariable] = []
    path_entries: list[EnvironmentHtmlPathEntry] = []
    mode: Literal["variables", "path"]
    if which in ("PATH", "p"):
        mode = "path"
        path_entries = read_path_entries(entries=get_path_entries())
    else:
        mode = "variables"
        variables = read_environment_variables(environment=os.environ)
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
