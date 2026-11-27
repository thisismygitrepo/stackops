import platform
import shutil

from stackops.scripts.python.helpers.helpers_utils.autostart import collect_autostart_entries
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import (
    DESKTOP_FILE_SOURCE,
    EVERY_ACCOUNT_SOURCE_STARTS,
    RUN_KEY_SOURCE,
    STARTUP_FOLDER_SOURCE,
    SYSTEMD_SOURCE,
)
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux import read_linux_own_entries
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_macos import read_macos
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import StartupEntry, StartupPicture, StartupProblem
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_windows import read_windows_own_entries


# Linux and Windows: the command's own list, with the entries that start for the person alone read again by the page itself, since those
# are the ones it can switch and the command says too little about them. They are told apart by the name the command lists them under.
# The rest stays as the command gives it: what it does not say about an entry (its file, whether it runs now) is left empty, and it has no
# switch. Of those, what starts at sign-in is taken to be the person's own unless its name says it is there for every account.
def _listed_picture(system: str, own_entries: list[StartupEntry], own_sources: tuple[str, ...]) -> StartupPicture:
    entries: list[StartupEntry] = []
    for entry in collect_autostart_entries():
        if entry.scope == "login" and entry.source in own_sources:
            continue
        every_account = entry.scope == "boot" or entry.source.startswith(EVERY_ACCOUNT_SOURCE_STARTS)
        entries.append(
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
                whose="system" if entry.stock else "apps" if every_account else "yours",
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
                lock="system" if entry.stock else "administrator" if every_account else "no_switch",
            )
        )
    return StartupPicture(platform=system, entries=[*entries, *own_entries], notes=[])


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
            case "Linux":
                return _listed_picture(system=system, own_entries=read_linux_own_entries(), own_sources=(SYSTEMD_SOURCE, DESKTOP_FILE_SOURCE))
            case "Windows":
                return _listed_picture(system=system, own_entries=read_windows_own_entries(), own_sources=(RUN_KEY_SOURCE, STARTUP_FOLDER_SOURCE))
            case _:
                return StartupProblem(reason="unsupported", message=f"""StackOps does not know where {system or "this system"} keeps what starts on its own.""")
    except RuntimeError as error:
        return StartupProblem(reason="failed", message=str(error))
