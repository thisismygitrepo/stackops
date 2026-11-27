import contextlib
import io
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil

from stackops.scripts.python.helpers.helpers_utils.autostart_common import categorize

# The command's own two readers of launchd, which it keeps to itself. Used as they are, so the page lists exactly what the command lists.
from stackops.scripts.python.helpers.helpers_utils.autostart_macos import (
    _disabled_overrides,  # pyright: ignore[reportPrivateUsage]
    _launch_triggers,  # pyright: ignore[reportPrivateUsage]
)
from stackops.scripts.python.helpers.helpers_utils.autostart_macos_login import collect_login_items
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import LAUNCHD_SYSTEM_SOURCE, LAUNCHD_USER_SOURCE, LOGIN_ITEMS_REFUSED, MANAGED_LABEL_STARTS
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_launchd import (
    LaunchdJob,
    LaunchdLocation,
    LoadedService,
    launchd_locations,
    loaded_services,
    program_of,
    read_jobs,
    session_domain,
    user_domain,
)
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import EntryAction, LockReason, StartManner, StartupEntry, StartupPicture
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_naming import app_of, owner_of, readable_title


def _manner_of(triggers: list[str]) -> StartManner:
    if "at load" in triggers or "kept alive" in triggers:
        return "always"
    return "timer" if any(trigger == "scheduled" or trigger.startswith("every ") for trigger in triggers) else "demand"


def _location_jobs(location: LaunchdLocation) -> list[LaunchdJob]:
    return read_jobs(sorted(location.directory.glob("*.plist"))) if location.directory.is_dir() else []


# The same jobs, names, descriptions and categories as the command gives, plus the ones that are turned off: the command leaves those out, and
# a page that can turn one off has to keep showing it so it can be turned back on. `loaded` is searched in order, first match wins.
# The person's own agents can be switched and removed. An agent an app installed for every account starts in the person's own session, where
# launchd's switch for the account covers it as well, so it can be switched but not removed: its file is the administrator's. The ones that
# guard or manage the computer are left out of that. What starts with the computer is the administrator's altogether.
def _launchd_entries(location: LaunchdLocation, jobs: list[LaunchdJob], turned_off: dict[str, bool], loaded: list[dict[str, LoadedService]]) -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    for job in jobs:
        triggers = _launch_triggers(job.keys)
        if not triggers:
            continue
        program = program_of(job.keys)
        described = "; ".join(triggers)
        enabled = not turned_off.get(job.label, job.keys.get("Disabled") is True)
        service = next((services[job.label] for services in loaded if job.label in services), None)
        yours = location.whose == "yours"
        switch: EntryAction = "turn_off" if enabled else "turn_on"
        lock: LockReason = (
            "" if yours
            else "system" if location.stock
            else "administrator" if location.scope == "boot"
            else "managed" if job.label.lower().startswith(MANAGED_LABEL_STARTS)
            else ""
        )
        entries.append(
            StartupEntry(
                id=f"""launchd:{job.path}""",
                kind="launchd",
                name=job.label,
                title=readable_title(job.label),
                description=f"""{Path(program).name} ({described})""" if program else described,
                category=categorize(job.label, fallback="system-os" if location.stock else "apps-services"),
                scope=location.scope,
                source=LAUNCHD_USER_SOURCE if yours else LAUNCHD_SYSTEM_SOURCE,
                stock=location.stock,
                whose=location.whose,
                owner="macOS" if location.stock else owner_of(label=job.label, program=program),
                enabled=enabled,
                manner=_manner_of(triggers),
                triggers=triggers,
                program=program,
                file=str(job.path),
                live="idle" if service is None else "waiting" if service.pid is None else "running",
                pid=service.pid if service is not None else None,
                last_exit=service.last_exit if service is not None else None,
                actions=[switch, "remove"] if yours else [switch] if lock == "" else [],
                lock=lock,
            )
        )
    return entries


# The login items as the command reads them. What it would print to the terminal when macOS does not let it look is handed back as a note,
# so the page can say it. An item counts as running when a process runs from inside the app it names.
def read_login_item_entries() -> tuple[list[StartupEntry], list[str]]:
    said = io.StringIO()
    with contextlib.redirect_stderr(said):
        items = collect_login_items()
    # Anything else that reached the terminal's error output in that moment is the server's own, so it goes back where it was headed.
    lines = [line.strip() for line in said.getvalue().splitlines() if line.strip()]
    sys.stderr.write("".join(f"""{line}\n""" for line in lines if not line.startswith(LOGIN_ITEMS_REFUSED)))
    running = [(process.pid, exe) for process in psutil.process_iter(["exe"]) if isinstance(exe := process.info["exe"], str) and exe]
    entries: list[StartupEntry] = []
    for item in items:
        path = item.description if item.description.startswith("/") else ""
        pid = next((pid for pid, exe in running if exe == path or exe.startswith(f"""{path}/""")), None) if path else None
        entries.append(
            StartupEntry(
                id=f"""login:{item.name}:{path}""",
                kind="login_item",
                name=item.name,
                title=item.name,
                description=item.description,
                category=item.category,
                scope=item.scope,
                source=item.source,
                stock=item.stock,
                whose="system" if item.stock else "yours",
                owner="macOS" if item.stock else app_of(path),
                enabled=True,
                manner="always",
                triggers=[],
                program=path,
                file="",
                live="running" if pid is not None else "idle" if path else "unknown",
                pid=pid,
                last_exit=None,
                actions=["remove"] if path and not item.stock else [],
                lock="system" if item.stock else "" if path else "unlocated",
            )
        )
    return entries, [line for line in lines if line.startswith(LOGIN_ITEMS_REFUSED)]


# Everything is asked for at once: the folders, launchd's own lists and the login items do not wait for each other, and the slowest of them,
# the login items, takes a third of a second.
def read_macos() -> StartupPicture:
    locations = launchd_locations()
    with ThreadPoolExecutor(max_workers=12) as pool:
        login = pool.submit(read_login_item_entries)
        system_off = pool.submit(_disabled_overrides, "system")
        user_off = pool.submit(_disabled_overrides, user_domain())
        system_loaded = pool.submit(loaded_services, "system")
        session_loaded = pool.submit(loaded_services, session_domain())
        user_loaded = pool.submit(loaded_services, user_domain())
        found = [pool.submit(_location_jobs, location) for location in locations]
    entries: list[StartupEntry] = []
    for location, jobs in zip(locations, found, strict=True):
        at_boot = location.scope == "boot"
        entries.extend(
            _launchd_entries(
                location=location,
                jobs=jobs.result(),
                turned_off=system_off.result() if at_boot else user_off.result(),
                loaded=[system_loaded.result()] if at_boot else [session_loaded.result(), user_loaded.result()],
            )
        )
    login_entries, notes = login.result()
    return StartupPicture(platform="macOS", entries=[*entries, *login_entries], notes=notes)


# Only what starts in the person's own session and is not part of macOS, read afresh: what an action is checked against before it is
# carried out.
def read_session_launchd_entries() -> list[StartupEntry]:
    turned_off = _disabled_overrides(user_domain())
    loaded = [loaded_services(session_domain()), loaded_services(user_domain())]
    return [
        entry
        for location in launchd_locations()
        if location.scope == "login" and not location.stock
        for entry in _launchd_entries(location=location, jobs=_location_jobs(location), turned_off=turned_off, loaded=loaded)
    ]
