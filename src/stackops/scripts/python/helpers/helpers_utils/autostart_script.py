import getpass
import os
import platform
import plistlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_utils.autostart_script_constants import ENTRY_PREFIX, LAUNCHCTL, LINGERING_ACCOUNTS_FOLDER, SYSTEM_NAMES
from stackops.scripts.python.helpers.helpers_utils.autostart_script_entries import entry_file_of, script_of_entry
from stackops.utils.schemas.startup.startup_types import StartupWhen

type StartupScriptFailureReason = Literal[
    "unsupported_system", "unsupported_kind", "missing_program", "missing_script", "already_added", "not_added", "system_refused",
    "boot_needs_administrator", "cannot_remember",
]

NAME_GAPS = re.compile(r"[^A-Za-z0-9_]+")


@dataclass(frozen=True)
class StartupScriptAdded:
    entry_file: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class StartupScriptRemoved:
    entry_file: Path
    script_path: Path


@dataclass(frozen=True)
class StartupScriptFailure:
    reason: StartupScriptFailureReason
    message: str


def _refusal(arguments: list[str]) -> str | None:
    process = subprocess.run(arguments, capture_output=True, text=True, check=False)
    return None if process.returncode == 0 else " ".join((process.stderr or process.stdout).split()) or f"""{arguments[0]} ended with code {process.returncode}"""


def _systemd_quoted(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'''"{escaped}"'''


# A .py is a standalone file that names what it needs in itself, so uv runs it and it is the same script on every system. A shell script
# belongs to the system it is written for. The program is named by its full path: what starts at sign-in is not started from a shell.
def _command_of(script_path: Path, system: str, search_path: str) -> tuple[str, ...] | StartupScriptFailure:
    arguments: tuple[str, ...]
    match (script_path.suffix, system):
        case (".py", _):
            runner, arguments = "uv", ("run", "--no-project")
        case (".sh", "Darwin" | "Linux"):
            runner, arguments = "bash", ()
        case (".ps1", "Windows"):
            runner, arguments = "pwsh", ("-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")
        case _:
            return StartupScriptFailure(
                reason="unsupported_kind",
                message=f"""{script_path.name} cannot start on its own here. A startup script is a .py file, a .sh file on macOS and Linux, or a .ps1 file on Windows.""",
            )
    program = shutil.which(runner, path=search_path)
    if program is None:
        return StartupScriptFailure(reason="missing_program", message=f"""{script_path.name} is run by {runner}, which is not on PATH.""")
    return (program, *arguments, str(script_path))


# The entry is written and switched on, and nothing is started: the script first runs at the next sign-in. `search_path` is the PATH of
# whoever adds it. The script is given it, since what the system starts by itself otherwise finds little more than the system's own programs.
# `boot` is for a computer nobody signs in to. The entry is the same one, of the person's own account: on Linux the account's services are
# told to start with the computer and stay (lingering), which holds for everything the account starts at sign-in. An account may switch
# that on for itself where the system lets it; on a server it is often the administrator's to do, once. On macOS and Windows only an
# administrator can have something start before a sign-in, so it is refused there.
def add_startup_script(script_path: Path, search_path: str, when: StartupWhen) -> StartupScriptAdded | StartupScriptFailure:
    system = platform.system()
    slug = NAME_GAPS.sub("-", script_path.stem).strip("-")
    entry_file = entry_file_of(slug=slug, system=system)
    if entry_file is None:
        return StartupScriptFailure(reason="unsupported_system", message=f"""StackOps does not know how to start a script at sign-in on {system or "this system"}.""")
    if not slug:
        return StartupScriptFailure(reason="unsupported_kind", message=f"""{script_path.name} has no letters or digits in its name to call its startup entry by.""")
    command = _command_of(script_path=script_path, system=system, search_path=search_path)
    if isinstance(command, StartupScriptFailure):
        return command
    if entry_file.exists():
        return StartupScriptFailure(reason="already_added", message=f"""A script called {slug} already starts at sign-in.""")
    match (when, system):
        case ("login", _):
            pass
        case ("boot", "Linux"):
            account = getpass.getuser()
            lingering_refused = None if LINGERING_ACCOUNTS_FOLDER.joinpath(account).exists() else _refusal(["loginctl", "enable-linger", account])
            if lingering_refused is not None:
                return StartupScriptFailure(
                    reason="system_refused",
                    message=f"""{script_path.name} can only start before you sign in once your account's services start with the computer, and the system did not agree to that: {lingering_refused}. An administrator allows it with `sudo loginctl enable-linger {account}`. Add the script again after that.""",
                )
        case _:
            return StartupScriptFailure(
                reason="boot_needs_administrator",
                message=f"""{script_path.name} cannot start when the computer starts on {SYSTEM_NAMES[system]}: that takes an administrator, and StackOps only sets up what starts for your own account. It can start when you sign in.""",
            )
    entry_file.parent.mkdir(parents=True, exist_ok=True)
    match system:
        case "Darwin":
            label = entry_file.stem
            log_file = Path.home() / "Library" / "Logs" / f"""{ENTRY_PREFIX}{slug}.log"""
            entry_file.write_bytes(
                plistlib.dumps({
                    "Label": label,
                    "ProgramArguments": list(command),
                    "RunAtLoad": True,
                    "WorkingDirectory": str(Path.home()),
                    "EnvironmentVariables": {"PATH": search_path},
                    "StandardOutPath": str(log_file),
                    "StandardErrorPath": str(log_file),
                })
            )
            # A label that was once turned off stays off in launchd's own records, also after its file is gone.
            refusal = _refusal([LAUNCHCTL, "enable", f"""user/{os.getuid()}/{label}"""])
        case "Linux":
            exec_start = " ".join(_systemd_quoted(argument.replace("$", "$$")) for argument in command)
            environment = _systemd_quoted(f"""PATH={search_path}""")
            entry_file.write_text(
                f"""[Unit]
Description=StackOps startup script {slug}

[Service]
ExecStart={exec_start}
Environment={environment}

[Install]
WantedBy=default.target
""",
                encoding="utf-8",
            )
            refusal = _refusal(["systemctl", "--user", "daemon-reload"]) or _refusal(["systemctl", "--user", "enable", entry_file.name])
        case _:
            entry_file.write_text(f"""@echo off\nchcp 65001 >nul\n{subprocess.list2cmdline(command).replace("%", "%%")}\n""", encoding="utf-8", newline="\r\n")
            refusal = None
    if refusal is not None:
        entry_file.unlink()
        return StartupScriptFailure(reason="system_refused", message=f"""The system did not take the startup entry for {script_path.name}: {refusal}""")
    return StartupScriptAdded(entry_file=entry_file, command=command)


# Named by the script, as when it was added: its file name, or a path to it. The script itself is left alone, and is stopped if this
# sign-in started it.
def remove_startup_script(script_name: str) -> StartupScriptRemoved | StartupScriptFailure:
    system = platform.system()
    slug = NAME_GAPS.sub("-", Path(script_name).stem).strip("-")
    entry_file = entry_file_of(slug=slug, system=system)
    if entry_file is None:
        return StartupScriptFailure(reason="unsupported_system", message=f"""StackOps does not know how to start a script at sign-in on {system or "this system"}.""")
    if not entry_file.is_file():
        return StartupScriptFailure(reason="not_added", message=f"""No script called {slug} starts at sign-in.""")
    script_path = script_of_entry(entry_file=entry_file, system=system)
    match system:
        case "Darwin":
            targets = [f"""{domain}/{os.getuid()}/{entry_file.stem}""" for domain in ("gui", "user")]
            loaded = [target for target in targets if subprocess.run([LAUNCHCTL, "print", target], capture_output=True, check=False).returncode == 0]
            refusal = next((said for target in loaded if (said := _refusal([LAUNCHCTL, "bootout", target])) is not None), None)
        case "Linux":
            refusal = _refusal(["systemctl", "--user", "disable", "--now", entry_file.name])
        case _:
            refusal = None
    if refusal is not None:
        return StartupScriptFailure(reason="system_refused", message=f"""The system did not let go of the startup entry {entry_file.name}: {refusal}""")
    entry_file.unlink()
    if system == "Linux":
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=False)
    return StartupScriptRemoved(entry_file=entry_file, script_path=script_path)
