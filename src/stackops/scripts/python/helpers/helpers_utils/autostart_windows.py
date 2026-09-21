import base64
import json
import shutil
import subprocess
from pathlib import Path
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_utils.autostart_common import (
    AutostartEntry,
    categorize,
)


class WindowsAutostartRecord(TypedDict):
    name: str
    description: str
    scope: Literal["boot", "login"]
    source: str
    stock: bool


def collect_windows_entries() -> list[AutostartEntry]:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        raise RuntimeError("Windows autostart inspection requires Windows PowerShell (powershell.exe) on PATH")
    try:
        script = Path(__file__).with_suffix(".ps1").read_text(encoding="utf-8")
        command = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        process = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"""Could not run Windows autostart inspection: {error}""") from error
    if process.returncode != 0:
        detail = process.stderr.strip() or f"""PowerShell exited with code {process.returncode}"""
        raise RuntimeError(f"""Windows autostart inspection failed: {detail}""")
    try:
        records = cast(list[WindowsAutostartRecord], json.loads(process.stdout))
    except json.JSONDecodeError as error:
        raise RuntimeError("Windows autostart inspection returned invalid JSON") from error
    return [
        AutostartEntry(
            name=record["name"],
            description=record["description"],
            category=categorize(record["name"], fallback="system-os" if record["stock"] else "apps-services"),
            scope=record["scope"],
            source=record["source"],
            stock=record["stock"],
        )
        for record in records
    ]
