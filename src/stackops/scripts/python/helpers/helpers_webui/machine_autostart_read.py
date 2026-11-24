import platform
import shutil

from stackops.scripts.python.helpers.helpers_utils.autostart import collect_autostart_entries
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_macos import read_macos
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import StartupEntry, StartupPicture, StartupProblem


# Linux and Windows: the command's own list as it is. What it does not say about an entry (its file, whether it runs now) is left empty, and
# nothing can be changed from the page. An entry that starts at sign-in is taken to be the person's own.
def _listed_picture(system: str) -> StartupPicture:
    entries = [
        StartupEntry(
            id=f"""listed:{entry.source}:{entry.scope}:{entry.name}""",
            kind="listed",
            name=entry.name,
            title=entry.name.removesuffix(".service"),
            description=entry.description,
            category=entry.category,
            scope=entry.scope,
            source=entry.source,
            stock=entry.stock,
            whose="system" if entry.stock else "yours" if entry.scope == "login" else "apps",
            owner="",
            enabled=True,
            manner="always",
            triggers=[],
            program="",
            file="",
            live="unknown",
            pid=None,
            last_exit=None,
            actions=[],
        )
        for entry in collect_autostart_entries()
    ]
    return StartupPicture(platform=system, entries=entries, notes=[])


# Everything that starts on its own, or why it cannot be told. A system the command has no reader for is `unsupported`; a reader that
# stopped halfway is `failed`, with what it said.
def read_startup() -> StartupPicture | StartupProblem:
    system = platform.system()
    try:
        match system:
            case "Darwin":
                return read_macos()
            case "Linux" if shutil.which("systemctl") is None:
                return StartupProblem(reason="unsupported", message="This system does not use systemd, which is where StackOps looks for what starts on its own.")
            case "Linux" | "Windows":
                return _listed_picture(system)
            case _:
                return StartupProblem(reason="unsupported", message=f"""StackOps does not know where {system or "this system"} keeps what starts on its own.""")
    except RuntimeError as error:
        return StartupProblem(reason="failed", message=str(error))
