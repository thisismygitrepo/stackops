import platform
import shutil
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.autostart_entry import (
    NAME_GAPS,
    StartupEntryAdded,
    StartupEntryFailure,
    StartupEntryRemoved,
    add_startup_entry,
    remove_startup_entry,
)
from stackops.utils.schemas.startup.startup_types import StartupWhen


# A .py is a standalone file that names what it needs in itself, so uv runs it and it is the same script on every system. A shell script
# belongs to the system it is written for. The program is named by its full path: what starts at sign-in is not started from a shell.
def add_startup_script(script_path: Path, search_path: str, when: StartupWhen) -> StartupEntryAdded | StartupEntryFailure:
    arguments: tuple[str, ...]
    match (script_path.suffix, platform.system()):
        case (".py", _):
            runner, arguments = "uv", ("run", "--no-project")
        case (".sh", "Darwin" | "Linux"):
            runner, arguments = "bash", ()
        case (".ps1", "Windows"):
            runner, arguments = "pwsh", ("-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")
        case _:
            return StartupEntryFailure(
                reason="unsupported_kind",
                message=f"""{script_path.name} cannot start on its own here. A startup script is a .py file, a .sh file on macOS and Linux, or a .ps1 file on Windows.""",
            )
    program = shutil.which(runner, path=search_path)
    if program is None:
        return StartupEntryFailure(reason="missing_program", message=f"""{script_path.name} is run by {runner}, which is not on PATH.""")
    return add_startup_entry(
        kind="script", title=script_path.name, slug=NAME_GAPS.sub("-", script_path.stem).strip("-"), command=(program, *arguments, str(script_path)), search_path=search_path, when=when,
    )


# Named by the script, as when it was added: its file name, or a path to it.
def remove_startup_script(script_name: str) -> StartupEntryRemoved | StartupEntryFailure:
    return remove_startup_entry(kind="script", slug=NAME_GAPS.sub("-", Path(script_name).stem).strip("-"))
