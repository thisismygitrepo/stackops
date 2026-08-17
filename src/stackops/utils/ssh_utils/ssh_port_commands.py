import os
import shlex
import shutil
import subprocess
from pathlib import Path


type PrivilegePrefix = tuple[str, ...]


def authorize_privileged_commands() -> PrivilegePrefix:
    if os.geteuid() == 0:
        return ()
    if shutil.which("sudo") is None:
        raise RuntimeError("Root privileges are required. Install sudo or run change-port as root.")
    result = subprocess.run(("sudo", "-v"), check=False)
    if result.returncode != 0:
        raise RuntimeError("Unable to obtain root privileges with sudo; run `sudo -v`, then retry.")
    return ("sudo",)


def run_command(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def capture_checked_command(command: tuple[str, ...], failure_message: str) -> str:
    result = run_command(command)
    if result.returncode == 0:
        return result.stdout
    error_output = result.stderr.strip() or result.stdout.strip()
    suffix = f": {error_output}" if error_output != "" else f" (exit code {result.returncode})"
    raise RuntimeError(f"{failure_message}{suffix}\nCommand: {shlex.join(command)}")


def run_checked_command(command: tuple[str, ...], failure_message: str) -> None:
    capture_checked_command(command=command, failure_message=failure_message)


def write_privileged_text(path: Path, content: str, privilege_prefix: PrivilegePrefix) -> None:
    command = (*privilege_prefix, "tee", str(path))
    result = subprocess.run(command, input=content, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return
    error_output = result.stderr.strip() or result.stdout.strip()
    suffix = f": {error_output}" if error_output != "" else f" (exit code {result.returncode})"
    raise RuntimeError(f"Failed to write {path}{suffix}")


def read_privileged_text(path: Path, privilege_prefix: PrivilegePrefix) -> str:
    return capture_checked_command(
        command=(*privilege_prefix, "cat", str(path)),
        failure_message=f"Failed to read {path}",
    )


def privileged_path_exists(path: Path, privilege_prefix: PrivilegePrefix) -> bool:
    result = run_command((*privilege_prefix, "test", "-e", str(path)))
    return result.returncode == 0
