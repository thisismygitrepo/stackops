import subprocess
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import GONE_MESSAGE, LAUNCHCTL, LOCKED_MESSAGE, OSASCRIPT
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_detail import find_launchd_job
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_launchd import loaded_services, session_domain, user_agents_location, user_domain
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_macos import read_own_launchd_entries
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import EntryAction, StartupEntry, StartupProblem

# The system's own way of putting a file in the Trash, so it lands where the person expects and can be dragged back out. Answers with what
# macOS said when it could not.
TRASH_SCRIPT = """function run(argv) {
  ObjC.import("Foundation");
  const error = $();
  const done = $.NSFileManager.defaultManager.trashItemAtURLResultingItemURLError($.NSURL.fileURLWithPath(argv[0]), null, error);
  return done ? "" : ObjC.unwrap(error.localizedDescription);
}"""


def _said(process: subprocess.CompletedProcess[str]) -> str:
    return " ".join((process.stderr or process.stdout).split()) or f"""It ended with code {process.returncode}."""


# What is asked for is looked up in a fresh read of the person's own launch agents and only done when that read offers it. So a request can
# name nothing but a file in that one folder, and nothing that belongs to the system or to every account, whatever the page sends.
def _offered(identifier: str, action: EntryAction) -> StartupEntry | StartupProblem:
    if Path(identifier.removeprefix("launchd:")).parent != user_agents_location().directory:
        return StartupProblem(reason="refused", message=f"""It is not one of your own startup programs. {LOCKED_MESSAGE}""")
    entry = next((candidate for candidate in read_own_launchd_entries() if candidate["id"] == identifier), None)
    if entry is None:
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    if action not in entry["actions"]:
        return StartupProblem(reason="refused", message=f"""{entry["title"]}: {LOCKED_MESSAGE}""")
    return entry


def _loaded_in(label: str) -> str | None:
    return next((domain for domain in (session_domain(), user_domain()) if label in loaded_services(domain)), None)


def _unload(label: str) -> StartupProblem | None:
    domain = _loaded_in(label)
    if domain is None:
        return None
    process = subprocess.run([LAUNCHCTL, "bootout", f"""{domain}/{label}"""], capture_output=True, text=True, check=False)
    return None if process.returncode == 0 else StartupProblem(reason="failed", message=f"""macOS could not stop {label}: {_said(process)}""")


# Off is launchd's own switch for the account, the one `utils machine autostart` reads: the job is not loaded at the next sign-in. It is also
# stopped and unloaded now. The file is left as it is, which is what makes turning it back on possible.
def turn_off(identifier: str) -> StartupProblem | None:
    entry = _offered(identifier=identifier, action="turn_off")
    match entry:
        case StartupProblem():
            return entry
        case _:
            label = entry["name"]
    process = subprocess.run([LAUNCHCTL, "disable", f"""{user_domain()}/{label}"""], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return StartupProblem(reason="failed", message=f"""macOS could not turn {label} off: {_said(process)}""")
    return _unload(label)


# The switch is put back, and the job is loaded again the way a sign-in loads it, so it starts now if it is one that starts right away.
# A job that is kept out of the desktop session is left for the next sign-in to load.
def turn_on(identifier: str) -> StartupProblem | None:
    entry = _offered(identifier=identifier, action="turn_on")
    match entry:
        case StartupProblem():
            return entry
        case _:
            label = entry["name"]
    found = find_launchd_job(identifier)
    match found:
        case StartupProblem():
            return found
        case _:
            sessions = found[1].keys.get("LimitLoadToSessionType")
    process = subprocess.run([LAUNCHCTL, "enable", f"""{user_domain()}/{label}"""], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return StartupProblem(reason="failed", message=f"""macOS could not turn {label} back on: {_said(process)}""")
    kept_out = sessions is not None and "Aqua" not in (cast(list[object], sessions) if isinstance(sessions, list) else [sessions])
    if kept_out or _loaded_in(label) is not None:
        return None
    process = subprocess.run([LAUNCHCTL, "bootstrap", session_domain(), entry["file"]], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return StartupProblem(reason="failed", message=f"""{label} is on again and starts at your next sign-in, but macOS could not load it now: {_said(process)}""")
    return None


# Stopped and unloaded, then its file goes to the Trash. Nothing is deleted: the file can be dragged back into the folder it came from.
def remove_launch_agent(identifier: str) -> StartupProblem | None:
    entry = _offered(identifier=identifier, action="remove")
    match entry:
        case StartupProblem():
            return entry
        case _:
            problem = _unload(entry["name"])
    if problem is not None:
        return problem
    process = subprocess.run([OSASCRIPT, "-l", "JavaScript", "-e", TRASH_SCRIPT, entry["file"]], capture_output=True, text=True, check=False)
    refusal = _said(process) if process.returncode != 0 else process.stdout.strip()
    return StartupProblem(reason="failed", message=f"""The file could not be moved to the Trash: {refusal}""") if refusal else None
