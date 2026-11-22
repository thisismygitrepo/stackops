import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.installer_utils.constants import UNINSTALL_FAILURE_TAIL_LINES
from stackops.utils.installer_utils.install_request_logic import resolve_installer_pattern
from stackops.utils.installer_utils.installer_uninstall_command import derive_uninstall_command
from stackops.utils.schemas.installer.installer_types import InstallerData, get_normalized_arch, get_os_name
from stackops.utils.source_of_truth import INSTALL_VERSION_ROOT, LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH


@dataclass(frozen=True, slots=True)
class InstalledBinary:
    path: Path
    removal_command: str
    removal_problem: str


@dataclass(frozen=True, slots=True)
class BinaryRemoved:
    path: Path
    command: str


@dataclass(frozen=True, slots=True)
class BinaryKept:
    path: Path | None
    problem: str


# StackOps deletes only what its own installer puts in place: a program file directly in its install folder. A link there, or a program found
# anywhere else, belongs to a package manager or another installer, and deleting its executable would leave that installer's records wrong.
# Such an app is removed by that tool's own uninstall command when the catalog's install command gives one, and is otherwise left alone.
# Not verified by choice: that the program found was installed by the catalog's command. If it was not, the uninstall command fails or leaves
# the program in place, and `remove_installed_binary` reports that.
def locate_installed_binary(exe_name: str, installer_data: InstallerData) -> InstalledBinary | None:
    is_windows = platform.system() == "Windows"
    install_root = Path(WINDOWS_INSTALL_PATH if is_windows else LINUX_INSTALL_PATH)
    candidate = install_root.joinpath(f"""{exe_name.removesuffix(".exe")}.exe""" if is_windows else exe_name)
    is_link = candidate.is_symlink()
    # On Windows the install folder also holds the system's own app aliases, which are empty files.
    if not is_link and candidate.is_file() and candidate.stat().st_size > 0:
        return InstalledBinary(path=candidate, removal_command="", removal_problem="")
    found = str(candidate) if is_link else shutil.which(exe_name)
    if found is None:
        return None
    install_command = resolve_installer_pattern(installer_data=installer_data, operating_system=get_os_name(), architecture=get_normalized_arch())
    removal_command = None if install_command is None else derive_uninstall_command(install_command=install_command)
    if removal_command is not None:
        return InstalledBinary(path=Path(found), removal_command=removal_command, removal_problem="")
    return InstalledBinary(
        path=Path(found),
        removal_command="",
        removal_problem=f"""{candidate} is a link to {candidate.resolve()}, which another installer manages. Remove the app with that installer."""
        if is_link
        else f"""{found} is not a program file in {install_root}, the folder StackOps installs into, so something else manages it. Remove the app with the tool that installed it.""",
    )


# With `show_output` the uninstall command talks to the terminal, where it can ask for a password or a yes. Without it nothing is printed, so the
# caller's own output stays clean, and a command that asks a question stops with that question as its problem.
def remove_installed_binary(exe_name: str, installer_data: InstallerData, show_output: bool) -> BinaryRemoved | BinaryKept:
    located = locate_installed_binary(exe_name=exe_name, installer_data=installer_data)
    if located is None:
        return BinaryKept(path=None, problem=f"""{exe_name} is not installed on this machine.""")
    if located.removal_problem != "":
        return BinaryKept(path=located.path, problem=located.removal_problem)
    command = located.removal_command
    if command == "":
        try:
            located.path.unlink()
        except OSError as error:
            return BinaryKept(path=located.path, problem=f"""{located.path} could not be deleted: {error}""")
    else:
        if show_output:
            print(f"""📦 Running: {command}""", flush=True)
            exit_code = subprocess.run(command, shell=True, check=False).returncode
            said = "what it said is above"
        else:
            completed = subprocess.run(
                command, shell=True, check=False, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace"
            )
            exit_code = completed.returncode
            said = "\n".join([line for line in completed.stdout.splitlines() if line.strip() != ""][-UNINSTALL_FAILURE_TAIL_LINES:]) or "it said nothing"
        if exit_code != 0:
            return BinaryKept(path=located.path, problem=f"""`{command}` stopped with exit code {exit_code}: {said}""")
        if located.path.is_symlink() or located.path.exists():
            return BinaryKept(
                path=located.path,
                problem=f"""`{command}` finished without an error, but {located.path} is still there, so that copy came from somewhere else. Remove it with the tool that installed it.""",
            )
    INSTALL_VERSION_ROOT.joinpath(exe_name).unlink(missing_ok=True)
    return BinaryRemoved(path=located.path, command=command)
