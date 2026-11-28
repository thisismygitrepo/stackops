import getpass
import os
import platform
import plistlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_utils.autostart_script_constants import LAUNCHCTL, LINGERING_ACCOUNTS_FOLDER, SYSTEM_NAMES
from stackops.scripts.python.helpers.helpers_utils.autostart_script_entries import ENTRY_PREFIXES, entry_file_of, target_of_entry
from stackops.utils.schemas.startup.startup_types import StartupKind, StartupWhen

type StartupEntryFailureReason = Literal[
    "unsupported_system", "unsupported_kind", "missing_program", "missing_script", "missing_layout", "already_added", "not_added", "system_refused",
    "boot_needs_administrator", "cannot_remember",
]

NAME_GAPS = re.compile(r"[^A-Za-z0-9_]+")


@dataclass(frozen=True)
class StartupEntryAdded:
    entry_file: Path
    command: tuple[str, ...]


# `target` is what the entry started: a script's file, or a layout's name.
@dataclass(frozen=True)
class StartupEntryRemoved:
    entry_file: Path
    target: str


@dataclass(frozen=True)
class StartupEntryFailure:
    reason: StartupEntryFailureReason
    message: str


def _refusal(arguments: list[str]) -> str | None:
    process = subprocess.run(arguments, capture_output=True, text=True, check=False)
    return None if process.returncode == 0 else " ".join((process.stderr or process.stdout).split()) or f"""{arguments[0]} ended with code {process.returncode}"""


def _systemd_quoted(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'''"{escaped}"'''


# The entry is written and switched on, and nothing is started: `command` first runs at the next sign-in. Its last word is what
# `target_of_entry` reads back. `title` is what the thing is called in what is said about it, `slug` what its entry is named by.
# `search_path` is the PATH of whoever adds it. The command is given it, since what the system starts by itself otherwise finds little
# more than the system's own programs.
# `boot` is for a computer nobody signs in to. The entry is the same one, of the person's own account: on Linux the account's services are
# told to start with the computer and stay (lingering), which holds for everything the account starts at sign-in. An account may switch
# that on for itself where the system lets it; on a server it is often the administrator's to do, once. On macOS and Windows only an
# administrator can have something start before a sign-in, so it is refused there.
# A layout's command ends as soon as its sessions are up, and they have to outlive it: launchd is told not to stop what the command
# leaves behind. On Linux the command sees to that itself (`add_startup_layout`).
def add_startup_entry(kind: StartupKind, title: str, slug: str, command: tuple[str, ...], search_path: str, when: StartupWhen) -> StartupEntryAdded | StartupEntryFailure:
    system = platform.system()
    entry_file = entry_file_of(kind=kind, slug=slug, system=system)
    if entry_file is None:
        return StartupEntryFailure(reason="unsupported_system", message=f"""StackOps does not know how to start a {kind} on its own on {system or "this system"}.""")
    if not slug:
        return StartupEntryFailure(reason="unsupported_kind", message=f"""{title} has no letters or digits in its name to call its startup entry by.""")
    if entry_file.exists():
        return StartupEntryFailure(reason="already_added", message=f"""A {kind} called {slug} already starts on its own here.""")
    match (when, system):
        case ("login", _):
            pass
        case ("boot", "Linux"):
            account = getpass.getuser()
            lingering_refused = None if LINGERING_ACCOUNTS_FOLDER.joinpath(account).exists() else _refusal(["loginctl", "enable-linger", account])
            if lingering_refused is not None:
                return StartupEntryFailure(
                    reason="system_refused",
                    message=f"""{title} can only start before you sign in once your account's services start with the computer, and the system did not agree to that: {lingering_refused}. An administrator allows it with `sudo loginctl enable-linger {account}`. Add it again after that.""",
                )
        case _:
            return StartupEntryFailure(
                reason="boot_needs_administrator",
                message=f"""{title} cannot start when the computer starts on {SYSTEM_NAMES[system]}: that takes an administrator, and StackOps only sets up what starts for your own account. It can start when you sign in.""",
            )
    entry_file.parent.mkdir(parents=True, exist_ok=True)
    match system:
        case "Darwin":
            label = entry_file.stem
            log_file = Path.home() / "Library" / "Logs" / f"""{ENTRY_PREFIXES[kind]}{slug}.log"""
            entry_file.write_bytes(
                plistlib.dumps({
                    "Label": label,
                    "ProgramArguments": list(command),
                    "RunAtLoad": True,
                    **({"AbandonProcessGroup": True} if kind == "layout" else {}),
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
Description=StackOps startup {kind} {slug}

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
        return StartupEntryFailure(reason="system_refused", message=f"""{title}: the system did not take its startup entry: {refusal}""")
    return StartupEntryAdded(entry_file=entry_file, command=command)


# What the entry started is left alone, except that it is stopped if this sign-in started it.
def remove_startup_entry(kind: StartupKind, slug: str) -> StartupEntryRemoved | StartupEntryFailure:
    system = platform.system()
    entry_file = entry_file_of(kind=kind, slug=slug, system=system)
    if entry_file is None:
        return StartupEntryFailure(reason="unsupported_system", message=f"""StackOps does not know how to start a {kind} on its own on {system or "this system"}.""")
    if not entry_file.is_file():
        return StartupEntryFailure(reason="not_added", message=f"""No {kind} called {slug} starts on its own here.""")
    target = target_of_entry(entry_file=entry_file, system=system)
    match system:
        case "Darwin":
            domains = [f"""{domain}/{os.getuid()}/{entry_file.stem}""" for domain in ("gui", "user")]
            loaded = [domain for domain in domains if subprocess.run([LAUNCHCTL, "print", domain], capture_output=True, check=False).returncode == 0]
            refusal = next((said for domain in loaded if (said := _refusal([LAUNCHCTL, "bootout", domain])) is not None), None)
        case "Linux":
            refusal = _refusal(["systemctl", "--user", "disable", "--now", entry_file.name])
        case _:
            refusal = None
    if refusal is not None:
        return StartupEntryFailure(reason="system_refused", message=f"""The system did not let go of the startup entry {entry_file.name}: {refusal}""")
    entry_file.unlink()
    if system == "Linux":
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=False)
    return StartupEntryRemoved(entry_file=entry_file, target=target)
