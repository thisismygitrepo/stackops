import os
import plistlib
import re
import subprocess
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_utils.autostart_common import (
    AutostartEntry,
    AutostartScope,
    categorize,
)
from stackops.scripts.python.helpers.helpers_utils.autostart_macos_login import collect_login_items


def _disabled_overrides(domain: str) -> dict[str, bool]:
    process = subprocess.run(
        ["/bin/launchctl", "print-disabled", domain],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"""Cannot inspect launchd domain {domain}: {process.stderr.strip()}""")
    overrides: dict[str, bool] = {}
    for line in process.stdout.splitlines():
        if "=>" not in line:
            continue
        match = re.fullmatch(r'\s*"(.+)"\s*=>\s*(true|false|enabled|disabled)\s*', line)
        if match is None:
            raise RuntimeError(f"""Unexpected launchctl disabled-state output for {domain}""")
        overrides[match[1]] = match[2] in {"true", "disabled"}
    return overrides


def _launch_triggers(job: dict[str, object]) -> list[str]:
    triggers: list[str] = []
    if job.get("RunAtLoad") is True:
        triggers.append("at load")
    keep_alive = job.get("KeepAlive")
    if keep_alive is True or isinstance(keep_alive, dict) and keep_alive:
        triggers.append("kept alive")
    interval = job.get("StartInterval")
    if isinstance(interval, int) and interval > 0:
        triggers.append(f"""every {interval}s""")
    calendar = job.get("StartCalendarInterval")
    if isinstance(calendar, dict) or isinstance(calendar, list) and calendar:
        triggers.append("scheduled")
    for key, description in (
        ("WatchPaths", "path changes"),
        ("QueueDirectories", "queued files"),
        ("StartOnMount", "mount events"),
        ("Sockets", "socket demand"),
        ("LaunchEvents", "system events"),
    ):
        if job.get(key):
            triggers.append(description)
    services = job.get("MachServices")
    if isinstance(services, dict) and any(
        value is True or isinstance(value, dict) for value in cast(dict[str, object], services).values()
    ):
        triggers.append("service demand")
    return triggers


def _launchd_entries(
    directory: Path,
    scope: AutostartScope,
    stock: bool,
    overrides: dict[str, bool],
) -> list[AutostartEntry]:
    entries: list[AutostartEntry] = []
    if not directory.is_dir():
        return entries
    paths = sorted(directory.glob("*.plist"))
    if not paths:
        return entries
    process = subprocess.run(
        ["/usr/bin/plutil", "-convert", "xml1", "-o", "-", "--", *(str(path) for path in paths)],
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"""Cannot read launchd jobs in {directory}; plutil exited with status {process.returncode}. {detail}"""
        )
    documents = process.stdout.split(b"</plist>")
    if len(documents) != len(paths) + 1 or documents[-1].strip():
        raise RuntimeError(f"""plutil returned an unexpected number of property lists for {directory}""")
    for document in documents[:-1]:
        parsed: object = plistlib.loads(document.lstrip() + b"</plist>")
        if not isinstance(parsed, dict):
            continue
        job = cast(dict[str, object], parsed)
        label = job.get("Label")
        if not isinstance(label, str) or not label:
            continue
        if overrides.get(label, job.get("Disabled") is True):
            continue
        triggers = _launch_triggers(job)
        if not triggers:
            continue
        program = job.get("Program")
        arguments = job.get("ProgramArguments")
        if not isinstance(program, str) and isinstance(arguments, list) and arguments:
            program = cast(list[object], arguments)[0]
        description = "; ".join(triggers)
        if isinstance(program, str) and program:
            description = f"""{Path(program).name} ({description})"""
        entries.append(
            AutostartEntry(
                name=label,
                description=description,
                category=categorize(label, fallback="system-os" if stock else "apps-services"),
                scope=scope,
                source="launchd (user)" if directory == Path.home() / "Library" / "LaunchAgents" else "launchd (system)",
                stock=stock,
            )
        )
    return entries


def collect_macos_entries() -> list[AutostartEntry]:
    system_overrides = _disabled_overrides("system")
    user_overrides = _disabled_overrides(f"""user/{os.getuid()}""")
    entries: list[AutostartEntry] = []
    locations: tuple[tuple[Path, AutostartScope, bool], ...] = (
        (Path("/System/Library/LaunchDaemons"), "boot", True),
        (Path("/Library/LaunchDaemons"), "boot", False),
        (Path("/System/Library/LaunchAgents"), "login", True),
        (Path("/Library/LaunchAgents"), "login", False),
        (Path.home() / "Library" / "LaunchAgents", "login", False),
    )
    for directory, scope, stock in locations:
        entries.extend(
            _launchd_entries(
                directory=directory,
                scope=scope,
                stock=stock,
                overrides=system_overrides if scope == "boot" else user_overrides,
            )
        )
    entries.extend(collect_login_items())
    return entries
