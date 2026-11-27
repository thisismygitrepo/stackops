import json
import subprocess
from pathlib import Path

from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import DESKTOP_GROUP, GONE_MESSAGE, LOCKED_MESSAGE, SYSTEMCTL_USER, TURNED_OFF_UNITS_FILE
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux import read_linux_own_entries, read_turned_off_units
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import EntryAction, StartupProblem


# Off is systemd's own switch for the account, the one `utils machine autostart` reads, and the unit is stopped now as well. On puts the
# switch back and starts it. The unit's file is left as it is. What was turned off is written down, since systemd does not say.
def _switch_unit(unit: str, on: bool) -> StartupProblem | None:
    process = subprocess.run([*SYSTEMCTL_USER, "enable" if on else "disable", "--now", unit], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        said = " ".join((process.stderr or process.stdout).split()) or f"""It ended with code {process.returncode}."""
        return StartupProblem(reason="failed", message=f"""The system could not turn {unit} {"back on" if on else "off"}: {said}""")
    if not on:
        state = subprocess.run([*SYSTEMCTL_USER, "is-enabled", unit], capture_output=True, text=True, check=False)
        if state.stdout.strip() == "enabled":
            return StartupProblem(reason="failed", message=f"""{unit} still starts on its own: something other than your own settings turns it on.""")
    others = [name for name in read_turned_off_units() if name != unit]
    TURNED_OFF_UNITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TURNED_OFF_UNITS_FILE.write_text(json.dumps(others if on else [*others, unit]), encoding="utf-8")
    return None


# Off writes `Hidden=true` into the file's first group, which every desktop reads as "pass this file over". On takes the line out again.
# Nothing else in the file is touched, and whatever is open now stays open.
def _switch_desktop_file(path: Path, on: bool) -> StartupProblem | None:
    try:
        kept: list[bytes] = []
        group = b""
        for line in path.read_bytes().splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith(b"["):
                group = stripped
            if group == DESKTOP_GROUP and stripped.partition(b"=")[0].strip() == b"Hidden":
                continue
            kept.append(line)
            if stripped == DESKTOP_GROUP and not on:
                kept[-1:] = [line if line.endswith(b"\n") else line + b"\n", b"Hidden=true\n"]
        path.write_bytes(b"".join(kept))
    except OSError as error:
        return StartupProblem(reason="failed", message=f"""{path.name} could not be changed: {error}""")
    return None


# What is asked for is looked up in a fresh read of what starts for the person alone and only done when that read offers it. So a request
# can name nothing but a unit of their own or a file in their autostart folder, whatever the page sends.
def switch_linux_entry(identifier: str, on: bool) -> StartupProblem | None:
    action: EntryAction = "turn_on" if on else "turn_off"
    entry = next((candidate for candidate in read_linux_own_entries() if candidate["id"] == identifier), None)
    if entry is None:
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    if action not in entry["actions"]:
        return StartupProblem(reason="refused", message=f"""{entry["title"]}: {LOCKED_MESSAGE}""")
    match entry["kind"]:
        case "systemd":
            return _switch_unit(unit=entry["name"], on=on)
        case _:
            return _switch_desktop_file(path=Path(entry["file"]), on=on)
