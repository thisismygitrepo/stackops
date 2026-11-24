from pathlib import PurePosixPath

from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import MAKERS_BY_LABEL_START, MAKERS_BY_PROGRAM_START, REVERSED_DOMAIN_STARTS


# The words of a launchd label that say what the thing is, without the maker's name in front: com.example.sync-helper reads "Sync helper".
# A label that is not written back to front is shown as it is.
def readable_title(label: str) -> str:
    known_start = next((start for start in MAKERS_BY_LABEL_START if label.startswith(start)), None)
    parts = label.split(".")
    if known_start is not None:
        rest = label.removeprefix(known_start)
    elif len(parts) >= 3 and parts[0].lower() in REVERSED_DOMAIN_STARTS:
        rest = ".".join(parts[2:])
    else:
        rest = ""
    words = " ".join(rest.replace(".", " ").replace("_", " ").replace("-", " ").split())
    return words[0].upper() + words[1:] if words else label


def app_of(program: str) -> str:
    bundle = next((part for part in PurePosixPath(program).parts if part.endswith(".app")), None)
    return bundle.removesuffix(".app") if bundle is not None else ""


# Who a launchd job belongs to, from the best sign there is: the app its program sits in, then the maker named at the start of its label,
# then the package manager its program was installed by. Empty when nothing says.
def owner_of(label: str, program: str) -> str:
    app = app_of(program)
    if app:
        return app
    known = next((maker for start, maker in MAKERS_BY_LABEL_START.items() if label.startswith(start)), None)
    if known is not None:
        return known
    parts = label.split(".")
    if len(parts) >= 3 and parts[0].lower() in REVERSED_DOMAIN_STARTS:
        return parts[1].capitalize() if parts[1].islower() else parts[1]
    return next((maker for start, maker in MAKERS_BY_PROGRAM_START.items() if program.startswith(start)), "")
