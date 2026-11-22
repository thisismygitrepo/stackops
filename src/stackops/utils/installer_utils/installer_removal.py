import platform
import shutil
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.source_of_truth import INSTALL_VERSION_ROOT, LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH


@dataclass(frozen=True, slots=True)
class InstalledBinary:
    path: Path
    removal_problem: str


@dataclass(frozen=True, slots=True)
class BinaryRemoved:
    path: Path


@dataclass(frozen=True, slots=True)
class BinaryKept:
    path: Path | None
    problem: str


# StackOps deletes only what its own installer puts in place: a program file directly in its install folder. A link there, or a program found
# anywhere else, belongs to a package manager or another installer, and deleting its executable would leave that installer's records wrong.
def locate_installed_binary(exe_name: str) -> InstalledBinary | None:
    is_windows = platform.system() == "Windows"
    install_root = Path(WINDOWS_INSTALL_PATH if is_windows else LINUX_INSTALL_PATH)
    candidate = install_root.joinpath(f"""{exe_name.removesuffix(".exe")}.exe""" if is_windows else exe_name)
    if candidate.is_symlink():
        return InstalledBinary(
            path=candidate,
            removal_problem=f"""{candidate} is a link to {candidate.resolve()}, which another installer manages. Remove the app with that installer.""",
        )
    # On Windows the install folder also holds the system's own app aliases, which are empty files.
    if candidate.is_file() and candidate.stat().st_size > 0:
        return InstalledBinary(path=candidate, removal_problem="")
    found = shutil.which(exe_name)
    if found is None:
        return None
    return InstalledBinary(
        path=Path(found),
        removal_problem=f"""{found} is not a program file in {install_root}, the folder StackOps installs into, so something else manages it. Remove the app with the tool that installed it.""",
    )


def remove_installed_binary(exe_name: str) -> BinaryRemoved | BinaryKept:
    located = locate_installed_binary(exe_name=exe_name)
    if located is None:
        return BinaryKept(path=None, problem=f"""{exe_name} is not installed on this machine.""")
    if located.removal_problem != "":
        return BinaryKept(path=located.path, problem=located.removal_problem)
    try:
        located.path.unlink()
    except OSError as error:
        return BinaryKept(path=located.path, problem=f"""{located.path} could not be deleted: {error}""")
    INSTALL_VERSION_ROOT.joinpath(exe_name).unlink(missing_ok=True)
    return BinaryRemoved(path=located.path)
