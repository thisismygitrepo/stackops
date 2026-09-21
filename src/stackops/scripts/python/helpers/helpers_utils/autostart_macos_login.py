import json
import subprocess
from pathlib import Path
from typing import cast

import typer

from stackops.scripts.python.helpers.helpers_utils.autostart_common import AutostartEntry, categorize


def collect_login_items() -> list[AutostartEntry]:
    try:
        process = subprocess.run(
            [
                "/usr/bin/osascript",
                "-l",
                "JavaScript",
                "-e",
                """JSON.stringify(Application('/System/Library/CoreServices/System Events.app').loginItems().map(function(item) {
                    return {name: item.name(), path: item.path()};
                }))""",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        typer.echo("Login items could not be inspected: System Events did not respond within 10 seconds.", err=True)
        return []
    if process.returncode != 0:
        if any(code in process.stderr for code in ("-1743", "-1744", "-128")):
            typer.echo(
                "Login items could not be inspected: allow your terminal to control System Events in "
                "System Settings > Privacy & Security > Automation.",
                err=True,
            )
        else:
            details = process.stderr.strip().splitlines()
            reason = details[-1] if details else f"""osascript exited with code {process.returncode}"""
            typer.echo(f"""Login items could not be inspected: {reason}""", err=True)
        return []
    try:
        parsed: object = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("System Events returned invalid login-item data") from error
    if not isinstance(parsed, list):
        raise RuntimeError("System Events did not return a list of login items")
    entries: list[AutostartEntry] = []
    for item in cast(list[object], parsed):
        if not isinstance(item, dict):
            raise RuntimeError("System Events returned an invalid login item")
        fields = cast(dict[str, object], item)
        raw_name, raw_path = fields.get("name"), fields.get("path")
        path = raw_path if isinstance(raw_path, str) else ""
        name = raw_name if isinstance(raw_name, str) and raw_name else Path(path).name if path else "Unnamed login item"
        stock = bool(path) and Path(path).is_relative_to("/System")
        entries.append(
            AutostartEntry(
                name=name,
                description=path or "Location unavailable",
                category=categorize(name, fallback="desktop-session"),
                scope="login",
                source="macOS login items",
                stock=stock,
            )
        )
    return entries
