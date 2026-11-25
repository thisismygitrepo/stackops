import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from stackops.scripts.python.helpers.helpers_devops import vault_clipboard_clear
from stackops.scripts.python.helpers.helpers_devops.vault_constants import CLIPBOARD_CLEAR_SECONDS, CLIPBOARD_COMMANDS, ClipboardCommands, ClipboardPlatform


@dataclass(frozen=True)
class ClipboardToolMissing:
    program: str


@dataclass(frozen=True)
class ClipboardCopied:
    clear_after_seconds: int


@dataclass(frozen=True)
class ClipboardCopyFailed:
    program: str


def find_clipboard() -> ClipboardCommands | ClipboardToolMissing:
    system = platform.system()
    clipboard_platform: ClipboardPlatform = (
        "macos" if system == "Darwin" else "windows" if system == "Windows" else "wayland" if os.environ.get("WAYLAND_DISPLAY") else "x11"
    )
    commands = CLIPBOARD_COMMANDS[clipboard_platform]
    for program in (commands["copy"][0], commands["paste"][0]):
        if shutil.which(program) is None:
            return ClipboardToolMissing(program=program)
    return commands


def copy_with_timed_clear(commands: ClipboardCommands, value: str, clear_after_seconds: int) -> ClipboardCopied | ClipboardCopyFailed:
    copied = subprocess.run(
        commands["copy"], input=value.encode(commands["encoding"]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    if copied.returncode != 0:
        return ClipboardCopyFailed(program=commands["copy"][0])
    pasted = subprocess.run(commands["paste"], stdin=subprocess.DEVNULL, capture_output=True, check=False)
    if pasted.returncode != 0:
        return ClipboardCopyFailed(program=commands["paste"][0])
    request: vault_clipboard_clear.ClipboardClearRequest = {
        "seconds": clear_after_seconds,
        "digest": vault_clipboard_clear.clipboard_digest(pasted.stdout),
        "copy": list(commands["copy"]),
        "paste": list(commands["paste"]),
    }
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        creationflags = 0
    clearer = subprocess.Popen(  # pylint: disable=consider-using-with  # the clearer must outlive this command
        [sys.executable, "-I", str(Path(vault_clipboard_clear.__file__))],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=sys.platform != "win32",
        creationflags=creationflags,
    )
    if clearer.stdin is None:
        raise RuntimeError("The clipboard clearer was started without a pipe for its request.")
    clearer.stdin.write(json.dumps(request).encode("utf-8"))
    clearer.stdin.close()
    return ClipboardCopied(clear_after_seconds=clear_after_seconds)


def require_clipboard() -> ClipboardCommands:
    found = find_clipboard()
    if isinstance(found, ClipboardToolMissing):
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"Cannot copy: {found.program} is not installed, so this machine has no clipboard to copy to.", err=True)
        raise typer.Exit(code=1)
    return found


def copy_secret(commands: ClipboardCommands, value: str, label: str) -> None:
    outcome = copy_with_timed_clear(commands, value, CLIPBOARD_CLEAR_SECONDS)
    match outcome:
        case ClipboardCopyFailed():
            typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"Could not copy {label}: {outcome.program} failed.", err=True)
            raise typer.Exit(code=1)
        case ClipboardCopied():
            typer.echo(f"✅ Copied {label} to the clipboard. It is cleared in {outcome.clear_after_seconds} seconds unless something else is copied first.")
