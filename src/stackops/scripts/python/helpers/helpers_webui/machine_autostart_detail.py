import re
import subprocess
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import GONE_MESSAGE, LAUNCHCTL
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_launchd import (
    LaunchdJob,
    LaunchdLocation,
    launchd_locations,
    read_jobs,
    session_domain,
    user_domain,
)
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import CalendarSlot, StartupDetail, StartupProblem

RUNS = re.compile(r"^\truns = (\d+)$", re.MULTILINE)


# The job an entry of the list names. The file is only ever looked for in the folders the list is read from, whatever the page sends.
def find_launchd_job(identifier: str) -> tuple[LaunchdLocation, LaunchdJob] | StartupProblem:
    path = Path(identifier.removeprefix("launchd:"))
    location = next((candidate for candidate in launchd_locations() if candidate.directory == path.parent), None)
    if location is None or not identifier.startswith("launchd:") or path.suffix != ".plist":
        return StartupProblem(reason="unknown_entry", message="That is not one of the startup programs in the list.")
    if not path.is_file():
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    jobs = read_jobs([path])
    if not jobs:
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    return location, jobs[0]


def _texts(value: object) -> list[str]:
    return [item for item in cast(list[object], value) if isinstance(item, str)] if isinstance(value, list) else [value] if isinstance(value, str) else []


def _calendar(value: object) -> list[CalendarSlot]:
    slots = cast(list[object], value) if isinstance(value, list) else [value]
    found: list[CalendarSlot] = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        times = {key: amount for key, amount in cast(dict[str, object], slot).items() if isinstance(amount, int)}
        found.append(CalendarSlot(month=times.get("Month"), day=times.get("Day"), weekday=times.get("Weekday"), hour=times.get("Hour"), minute=times.get("Minute")))
    return found


# How often launchd has started the job since the domain it is loaded in began, or nothing when it is not loaded there.
def _runs(label: str, domains: list[str]) -> int | None:
    for domain in domains:
        process = subprocess.run([LAUNCHCTL, "print", f"""{domain}/{label}"""], capture_output=True, text=True, check=False)
        counted = RUNS.search(process.stdout) if process.returncode == 0 else None
        if counted is not None:
            return int(counted[1])
    return None


# The rest about one launchd job, read when its detail is opened: how it is started, what it is given, and where its output goes.
def read_startup_detail(identifier: str) -> StartupDetail | StartupProblem:
    found = find_launchd_job(identifier)
    match found:
        case StartupProblem():
            return found
        case _:
            location, job = found
    keys = job.keys
    directory = keys.get("WorkingDirectory")
    account = keys.get("UserName")
    return StartupDetail(
        arguments=_texts(keys.get("ProgramArguments"))[1:],
        working_directory=directory if isinstance(directory, str) else "",
        run_as=account if isinstance(account, str) else "",
        output_files=list(dict.fromkeys(_texts(keys.get("StandardOutPath")) + _texts(keys.get("StandardErrorPath")))),
        calendar=_calendar(keys.get("StartCalendarInterval")),
        watched=_texts(keys.get("WatchPaths")) + _texts(keys.get("QueueDirectories")),
        runs=_runs(label=job.label, domains=["system"] if location.scope == "boot" else [session_domain(), user_domain()]),
    )
