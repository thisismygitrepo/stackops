import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_utils.autostart_common import categorize, is_stock

# The command's own reader of what is turned on. Used as it is, so the page lists exactly the units the command lists.
from stackops.scripts.python.helpers.helpers_utils.autostart_linux import _list_enabled_services  # pyright: ignore[reportPrivateUsage]
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import (
    DESKTOP_FILE_SOURCE,
    DESKTOP_FILES_FOLDER,
    DESKTOP_GROUP,
    EVERY_ACCOUNT_UNITS_FOLDER,
    OWN_UNITS_FOLDER,
    SYSTEMCTL_USER,
    SYSTEMD_SOURCE,
    TURNED_OFF_UNITS_FILE,
    UNIT_FACTS,
)
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import LockReason, StartupEntry

PROGRAM_OF_UNIT = re.compile(r"path=(.+?) ; ")


def read_turned_off_units() -> list[str]:
    return cast(list[str], json.loads(TURNED_OFF_UNITS_FILE.read_text(encoding="utf-8"))) if TURNED_OFF_UNITS_FILE.is_file() else []


# What systemd says about each unit, by the unit's name. One run for all of them.
def _unit_facts(units: list[str]) -> dict[str, dict[str, str]]:
    if not units:
        return {}
    process = subprocess.run([*SYSTEMCTL_USER, "show", *units, f"""--property={UNIT_FACTS}""", "--no-pager"], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"""Cannot read the services of your account: {process.stderr.strip()}""")
    facts: dict[str, dict[str, str]] = {}
    for block in process.stdout.split("\n\n"):
        found: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition("=")
            found.setdefault(key, value)
        if "Id" in found:
            facts[found["Id"]] = found
    return facts


def _wanted_in(folder: Path, unit: str) -> bool:
    return any(wanting.joinpath(unit).is_symlink() for pattern in ("*.wants", "*.requires") for wanting in folder.glob(pattern))


# The units of the person's own service manager: the ones that are turned on, as the command lists them, and the ones the page turned off.
# A unit has a switch when it is the person's own settings that turn it on. One that is turned on for every account stays on whatever the
# person's settings say, and a template names no unit to switch, so neither has one.
def _unit_entries() -> list[StartupEntry]:
    turned_on = _list_enabled_services(user=True)
    remembered = [unit for unit in read_turned_off_units() if unit not in turned_on]
    facts = _unit_facts([unit for unit in [*turned_on, *remembered] if "@." not in unit])
    entries: list[StartupEntry] = []
    for unit in [*turned_on, *[unit for unit in remembered if facts.get(unit, {}).get("UnitFileState") == "disabled"]]:
        said = facts.get(unit, {})
        enabled = unit in turned_on
        stock = is_stock(unit)
        every_account = _wanted_in(folder=EVERY_ACCOUNT_UNITS_FOLDER, unit=unit)
        lock: LockReason = (
            "system" if stock
            else "no_switch" if "@." in unit
            else "" if not enabled
            else "administrator" if every_account
            else "" if _wanted_in(folder=OWN_UNITS_FOLDER, unit=unit)
            else "no_switch"
        )
        pid = int(said.get("MainPID", "0"))
        program = PROGRAM_OF_UNIT.search(said.get("ExecStart", ""))
        entries.append(
            StartupEntry(
                id=f"""systemd:{unit}""",
                kind="systemd",
                name=unit,
                title=unit.removesuffix(".service"),
                description=said.get("Description", ""),
                category=categorize(unit, fallback="system-os"),
                scope="login",
                source=SYSTEMD_SOURCE,
                stock=stock,
                whose="system" if stock else "apps" if every_account else "yours",
                owner="",
                enabled=enabled,
                manner="always",
                triggers=[],
                program=program[1] if program is not None else "",
                file=said.get("FragmentPath", ""),
                live="unknown" if not said else "running" if said.get("ActiveState") == "active" and pid > 0 else "waiting" if enabled else "idle",
                pid=pid or None,
                last_exit=int(said.get("ExecMainStatus", "0")) if said.get("ActiveState") == "failed" else None,
                actions=[] if lock != "" else ["turn_off"] if enabled else ["turn_on"],
                lock=lock,
            )
        )
    return entries


# What the first group of a desktop file says, by key. The other groups are about the file's extra actions.
def _desktop_keys(content: bytes) -> dict[str, str]:
    keys: dict[str, str] = {}
    group = b""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(b"["):
            group = stripped
        elif group == DESKTOP_GROUP and b"=" in stripped and not stripped.startswith(b"#"):
            key, _, value = stripped.decode("utf-8", errors="replace").partition("=")
            keys.setdefault(key.strip(), value.strip())
    return keys


# The desktop files in the person's autostart folder, named and sorted into kinds as the command does it. `Hidden=true` is the standard's
# own way of saying a file is to be passed over, so that is what off is.
def _desktop_file_entries() -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    for desktop_file in sorted(DESKTOP_FILES_FOLDER.glob("*.desktop")) if DESKTOP_FILES_FOLDER.is_dir() else []:
        try:
            keys = _desktop_keys(desktop_file.read_bytes())
        except OSError:
            continue
        title = keys.get("Name", desktop_file.stem)
        stock = is_stock(title) or is_stock(desktop_file.name)
        enabled = keys.get("Hidden", "").lower() != "true"
        try:
            words = shlex.split(keys.get("Exec", ""))
        except ValueError:
            words = []
        entries.append(
            StartupEntry(
                id=f"""desktop:{desktop_file}""",
                kind="sign_in",
                name=title,
                title=title,
                description=desktop_file.name,
                category=categorize(title, fallback="other"),
                scope="login",
                source=DESKTOP_FILE_SOURCE,
                stock=stock,
                whose="system" if stock else "yours",
                owner="",
                enabled=enabled,
                manner="always",
                triggers=[],
                program=words[0] if words else "",
                file=str(desktop_file),
                live="unknown",
                pid=None,
                last_exit=None,
                actions=[] if stock else ["turn_off"] if enabled else ["turn_on"],
                lock="system" if stock else "",
            )
        )
    return entries


# What starts at sign-in for the person alone, with more about each entry than the command says and a switch where there is one to use.
def read_linux_own_entries() -> list[StartupEntry]:
    return [*_unit_entries(), *_desktop_file_entries()]
