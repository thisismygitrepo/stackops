import os
import plistlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_utils.autostart_common import AutostartScope
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import LAUNCHCTL, PLUTIL
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import Whose

SERVICE_ROW = re.compile(r"\s+(\d+)\s+(\S+)\s+(.+)")


@dataclass(frozen=True)
class LaunchdLocation:
    directory: Path
    scope: AutostartScope
    stock: bool
    whose: Whose


@dataclass(frozen=True)
class LaunchdJob:
    path: Path
    label: str
    keys: dict[str, object]


@dataclass(frozen=True)
class LoadedService:
    domain: str
    pid: int | None
    last_exit: int | None


# The five folders `utils machine autostart` reads, in its order, with whose each one is.
def launchd_locations() -> tuple[LaunchdLocation, ...]:
    return (
        LaunchdLocation(directory=Path("/System/Library/LaunchDaemons"), scope="boot", stock=True, whose="system"),
        LaunchdLocation(directory=Path("/Library/LaunchDaemons"), scope="boot", stock=False, whose="apps"),
        LaunchdLocation(directory=Path("/System/Library/LaunchAgents"), scope="login", stock=True, whose="system"),
        LaunchdLocation(directory=Path("/Library/LaunchAgents"), scope="login", stock=False, whose="apps"),
        user_agents_location(),
    )


def user_agents_location() -> LaunchdLocation:
    return LaunchdLocation(directory=Path.home() / "Library" / "LaunchAgents", scope="login", stock=False, whose="yours")


def user_domain() -> str:
    return f"""user/{os.getuid()}"""


def session_domain() -> str:
    return f"""gui/{os.getuid()}"""


# Read the way the command reads them: one plutil run for the whole folder, which also takes the few files Python's own reader refuses.
def read_jobs(paths: list[Path]) -> list[LaunchdJob]:
    if not paths:
        return []
    process = subprocess.run([PLUTIL, "-convert", "xml1", "-o", "-", "--", *(str(path) for path in paths)], capture_output=True, check=False)
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"""Cannot read the launchd jobs in {paths[0].parent}; plutil exited with status {process.returncode}. {detail}""")
    documents = process.stdout.split(b"</plist>")
    if len(documents) != len(paths) + 1 or documents[-1].strip():
        raise RuntimeError(f"""plutil returned an unexpected number of property lists for {paths[0].parent}""")
    jobs: list[LaunchdJob] = []
    for path, document in zip(paths, documents[:-1], strict=True):
        parsed: object = plistlib.loads(document.lstrip() + b"</plist>")
        if not isinstance(parsed, dict):
            continue
        keys = cast(dict[str, object], parsed)
        label = keys.get("Label")
        if isinstance(label, str) and label:
            jobs.append(LaunchdJob(path=path, label=label, keys=keys))
    return jobs


def program_of(keys: dict[str, object]) -> str:
    program = keys.get("Program")
    arguments = keys.get("ProgramArguments")
    if not isinstance(program, str) and isinstance(arguments, list) and arguments:
        program = cast(list[object], arguments)[0]
    return program if isinstance(program, str) else ""


# What launchd has loaded in one of its domains, by label, with the process each one runs as and how it last ended. A label that is not here
# is not loaded: its file was added after the domain started, or it is turned off.
def loaded_services(domain: str) -> dict[str, LoadedService]:
    process = subprocess.run([LAUNCHCTL, "print", domain], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"""Cannot inspect launchd domain {domain}: {process.stderr.strip()}""")
    services: dict[str, LoadedService] = {}
    inside = False
    for line in process.stdout.splitlines():
        if line == "\tservices = {":
            inside = True
        elif inside and line == "\t}":
            break
        elif inside:
            row = SERVICE_ROW.fullmatch(line)
            if row is None:
                continue
            ended = row[2]
            services[row[3].strip()] = LoadedService(
                domain=domain, pid=int(row[1]) or None, last_exit=int(ended) if ended.lstrip("-").isdigit() else None,
            )
    return services
