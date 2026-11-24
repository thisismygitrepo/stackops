import contextlib
import io
import os
import shutil
from pathlib import Path
from typing import TypedDict

import stackops.settings.shells.nushell as nushell_assets
from stackops.profile.create_shell_profile import (
    NUSHELL_CONFIG_RELATIVE_PATH,
    NUSHELL_CONFIG_SOURCE_LINE,
    NUSHELL_ENV_RELATIVE_PATH,
    NUSHELL_ENV_SOURCE_LINE,
    get_nu_shell_profile_path,
)
from stackops.profile.migration_until_2028_01_bash_zsh_hook import STALE_HOOKS
from stackops.profile.shell_profile_source import ShellProfileSource, build_shell_profile_source
from stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_constants import (
    NUSHELL_RELOAD_COMMAND,
    SHELL_PROGRAMS,
    SetupBlocker,
    SetupRoute,
    ShellFamily,
    ShellId,
)
from stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_gives import ShellAlias, ShellExtra, read_shell_gives
from stackops.utils.path_reference import get_path_reference_library_relative_path
from stackops.utils.source_of_truth import CONFIG_ROOT, LIBRARY_ROOT


# One file a shell reads when it starts, and the line that makes it load StackOps' setup. Nothing of the file's text leaves this module: only
# whether that line is in it, and whether a line from before bash and zsh shared one setup script still is. `loads` is the file the line points at,
# `link_target` the file a profile that is a link leads to, and `problem` why a file that exists could not be read.
class ProfileFile(TypedDict):
    path: str
    exists: bool
    link_target: str
    problem: str
    line: str
    line_present: bool
    old_line_present: bool
    loads: str


# `login` marks the shell the account signs in with, which is the one the command's default choice acts on; on Windows that choice is PowerShell.
# `program` is empty for a shell that is not installed. `setup_current` says the setup files in place are the ones this StackOps ships.
# A shell that cannot be set up here has a `blocker` and nothing else filled in.
class ShellState(TypedDict):
    id: ShellId
    program: str
    login: bool
    route: SetupRoute
    blocker: SetupBlocker
    files: list[ProfileFile]
    setup_in_place: bool
    setup_current: bool
    reload_command: str
    aliases: list[ShellAlias]
    extras: list[ShellExtra]


# A folder that setting up fills with what StackOps ships.
class CopiedFolder(TypedDict):
    name: str
    path: str
    exists: bool


# `login_shell` is the name of the program the account signs in with, also when StackOps cannot set that one up; empty on Windows.
class ShellProfilesState(TypedDict):
    login_shell: str
    folders: list[CopiedFolder]
    shells: list[ShellState]


def _profile_file(path: Path, line: str, loads: Path) -> ProfileFile:
    exists = path.is_file()
    problem = ""
    lines: list[str] = []
    if exists:
        try:
            lines = [text.strip() for text in path.read_text(encoding="utf-8").splitlines()]
        except (OSError, UnicodeDecodeError) as error:
            problem = str(error)
    return {
        "path": str(path), "exists": exists, "link_target": str(path.resolve()) if path.is_symlink() else "", "problem": problem,
        "line": line, "line_present": line in lines, "old_line_present": any(text in STALE_HOOKS for text in lines), "loads": str(loads),
    }


# `setup_files` are the files the shell's lines load and the ones those pull in, as paths inside StackOps' settings. What the setup gives is read
# from the copies in place, which is what a terminal loads; before the first setup it is read from the files that would be copied.
def _usable_shell(
    shell_id: ShellId, program: str, login: bool, route: SetupRoute, files: list[ProfileFile], setup_files: tuple[Path, ...], family: ShellFamily, reload_command: str
) -> ShellState:
    in_place = all(CONFIG_ROOT.joinpath(setup_file).is_file() for setup_file in setup_files)
    current = in_place and all(CONFIG_ROOT.joinpath(setup_file).read_bytes() == LIBRARY_ROOT.joinpath(setup_file).read_bytes() for setup_file in setup_files)
    read_root = CONFIG_ROOT if in_place else LIBRARY_ROOT
    gives = read_shell_gives(family=family, text="\n".join(read_root.joinpath(setup_file).read_text(encoding="utf-8") for setup_file in setup_files))
    return {
        "id": shell_id, "program": program, "login": login, "route": route, "blocker": "", "files": files, "setup_in_place": in_place,
        "setup_current": current, "reload_command": reload_command, "aliases": gives["aliases"], "extras": gives["extras"],
    }


def _blocked_shell(shell_id: ShellId, program: str, blocker: SetupBlocker) -> ShellState:
    return {
        "id": shell_id, "program": program, "login": False, "route": "none", "blocker": blocker, "files": [], "setup_in_place": False,
        "setup_current": False, "reload_command": "", "aliases": [], "extras": [],
    }


# bash and zsh share one setup script. The command only ever acts on the one the account signs in with, so the other is set up by hand.
def _posix_shell(shell_id: ShellId, system_name: str, login_shell: str) -> ShellState:
    program = shutil.which(SHELL_PROGRAMS[shell_id]) or ""
    login = login_shell == SHELL_PROGRAMS[shell_id]
    if program == "" and not login:
        return _blocked_shell(shell_id=shell_id, program="", blocker="not_installed")
    source = build_shell_profile_source(system_name=system_name, shell_variable=f"""/bin/{SHELL_PROGRAMS[shell_id]}""", config_root=CONFIG_ROOT)
    return _usable_shell(
        shell_id=shell_id, program=program, login=login, route="default" if login else "manual",
        files=[_profile_file(path=source.profile_path, line=source.source_line, loads=source.init_script)],
        setup_files=(source.init_script.relative_to(CONFIG_ROOT),), family="posix", reload_command=source.reload_command,
    )


def _nushell_shell(login: bool) -> ShellState:
    program = shutil.which(SHELL_PROGRAMS["nushell"]) or ""
    if program == "":
        return _blocked_shell(shell_id="nushell", program="", blocker="not_installed")
    # The CLI's own lookup also prints a panel. Here it runs on every visit to the page, so what it prints is dropped.
    with contextlib.redirect_stdout(io.StringIO()):
        folder = get_nu_shell_profile_path()
    init_file = get_path_reference_library_relative_path(module=nushell_assets, path_reference=nushell_assets.INIT_PATH_REFERENCE)
    return _usable_shell(
        shell_id="nushell", program=program, login=login, route="nushell",
        files=[
            _profile_file(path=folder.joinpath("config.nu"), line=NUSHELL_CONFIG_SOURCE_LINE, loads=CONFIG_ROOT.joinpath(NUSHELL_CONFIG_RELATIVE_PATH)),
            _profile_file(path=folder.joinpath("env.nu"), line=NUSHELL_ENV_SOURCE_LINE, loads=CONFIG_ROOT.joinpath(NUSHELL_ENV_RELATIVE_PATH)),
        ],
        setup_files=(NUSHELL_CONFIG_RELATIVE_PATH, NUSHELL_ENV_RELATIVE_PATH, init_file), family="nushell", reload_command=NUSHELL_RELOAD_COMMAND,
    )


# `pwsh_sources` keeps PowerShell's answer about where its profile is: asking takes most of a second, and it does not change while the server runs.
def _pwsh_shell(system_name: str, shell_variable: str | None, pwsh_sources: dict[str, ShellProfileSource]) -> ShellState:
    program = shutil.which(SHELL_PROGRAMS["pwsh"]) or ""
    if system_name != "Windows":
        return _blocked_shell(shell_id="pwsh", program=program, blocker="other_system")
    if program == "":
        return _blocked_shell(shell_id="pwsh", program="", blocker="not_installed")
    if "pwsh" not in pwsh_sources:
        pwsh_sources["pwsh"] = build_shell_profile_source(system_name=system_name, shell_variable=shell_variable, config_root=CONFIG_ROOT)
    source = pwsh_sources["pwsh"]
    return _usable_shell(
        shell_id="pwsh", program=program, login=True, route="default",
        files=[_profile_file(path=source.profile_path, line=source.source_line, loads=source.init_script)],
        setup_files=(source.init_script.relative_to(CONFIG_ROOT),), family="pwsh", reload_command=source.reload_command,
    )


# The shells StackOps knows how to set up, each with where this machine stands on it. `shell_variable` is the server's own SHELL, which is what a
# setup run started from the page inherits and so what the command will read.
def read_shell_profiles(system_name: str, shell_variable: str | None, pwsh_sources: dict[str, ShellProfileSource]) -> ShellProfilesState:
    folders: list[CopiedFolder] = [
        {"name": name, "path": str(CONFIG_ROOT.joinpath(name)), "exists": CONFIG_ROOT.joinpath(name).is_dir()} for name in ("settings", "scripts")
    ]
    pwsh = _pwsh_shell(system_name=system_name, shell_variable=shell_variable, pwsh_sources=pwsh_sources)
    if system_name == "Windows":
        other_system: list[ShellState] = [
            _blocked_shell(shell_id=shell_id, program=shutil.which(SHELL_PROGRAMS[shell_id]) or "", blocker="other_system") for shell_id in ("zsh", "bash")
        ]
        return {"login_shell": "", "folders": folders, "shells": [pwsh, _nushell_shell(login=False), *other_system]}
    import pwd

    # The same reading the command gives it: SHELL when it is set, and the account's entry where a login would look otherwise.
    login_shell = Path(shell_variable if shell_variable is not None else pwd.getpwuid(os.getuid()).pw_shell).name
    posix: list[ShellState] = [_posix_shell(shell_id=shell_id, system_name=system_name, login_shell=login_shell) for shell_id in ("zsh", "bash")]
    return {"login_shell": login_shell, "folders": folders, "shells": [*posix, _nushell_shell(login=login_shell == SHELL_PROGRAMS["nushell"]), pwsh]}
