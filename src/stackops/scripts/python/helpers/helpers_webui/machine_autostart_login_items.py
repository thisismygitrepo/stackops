import json
import subprocess
from typing import cast

from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import GONE_MESSAGE, LOCKED_MESSAGE, OSASCRIPT, SCRIPT_SECONDS, SYSTEM_EVENTS
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_macos import read_login_item_entries
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import RemovedLoginItem, StartupProblem

# Asked of System Events, the same part of macOS the command reads the login items from. Taking an item off the list leaves the app alone.
REMOVE_SCRIPT = """function run(argv) {
  const events = Application(argv[0]);
  const found = events.loginItems().filter((item) => item.name() === argv[1] && item.path() === argv[2]);
  if (found.length === 0) return JSON.stringify({ found: false });
  const hidden = found[0].hidden();
  found[0].delete();
  return JSON.stringify({ found: true, hidden: hidden });
}"""
ADD_SCRIPT = """function run(argv) {
  const events = Application(argv[0]);
  if (!events.loginItems().some((item) => item.path() === argv[1])) events.loginItems.push(events.LoginItem({ path: argv[1], hidden: argv[2] === "true" }));
}"""


def _ask(script: str, arguments: list[str]) -> str | StartupProblem:
    try:
        process = subprocess.run([OSASCRIPT, "-l", "JavaScript", "-e", script, SYSTEM_EVENTS, *arguments], capture_output=True, text=True, check=False, timeout=SCRIPT_SECONDS)
    except subprocess.TimeoutExpired:
        return StartupProblem(reason="failed", message=f"""macOS did not answer within {SCRIPT_SECONDS} seconds. It may be waiting for you to allow StackOps to control System Events.""")
    if process.returncode == 0:
        return process.stdout.strip()
    said = process.stderr.strip().splitlines()
    return StartupProblem(reason="failed", message=said[-1] if said else f"""osascript ended with code {process.returncode}.""")


# Checked against a fresh read of the list, so only an item that is there now and is not part of the system can be taken off. What it was
# is handed back, which is all it takes to put it on the list again.
def remove_login_item(identifier: str) -> RemovedLoginItem | StartupProblem:
    entries, _notes = read_login_item_entries()
    entry = next((candidate for candidate in entries if candidate["id"] == identifier), None)
    if entry is None:
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    if "remove" not in entry["actions"]:
        return StartupProblem(reason="refused", message=f"""{entry["title"]}: {LOCKED_MESSAGE}""")
    answer = _ask(script=REMOVE_SCRIPT, arguments=[entry["name"], entry["program"]])
    match answer:
        case StartupProblem():
            return answer
        case _:
            outcome = cast(dict[str, object], json.loads(answer))
    if outcome.get("found") is not True:
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    return RemovedLoginItem(name=entry["name"], path=entry["program"], hidden=outcome.get("hidden") is True)


def restore_login_item(item: RemovedLoginItem) -> StartupProblem | None:
    answer = _ask(script=ADD_SCRIPT, arguments=[item["path"], "true" if item["hidden"] else "false"])
    return answer if isinstance(answer, StartupProblem) else None
