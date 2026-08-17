import os
import shlex
import stat
import subprocess
from pathlib import Path


type PrivilegePrefix = tuple[str, ...]
TRUSTED_SYSTEM_COMMAND_DIRECTORIES: tuple[Path, ...] = (
    Path("/usr/sbin"),
    Path("/usr/bin"),
    Path("/sbin"),
    Path("/bin"),
    Path("/usr/local/sbin"),
    Path("/usr/local/bin"),
)


def resolve_trusted_system_command(command_name: str) -> Path | None:
    if command_name == "" or "/" in command_name:
        raise ValueError(f"System command name must be a basename: {command_name!r}")
    for directory in TRUSTED_SYSTEM_COMMAND_DIRECTORIES:
        candidate = directory.joinpath(command_name)
        try:
            resolved = candidate.resolve(strict=True)
            file_status = resolved.stat()
            parent_statuses = tuple(
                parent.stat() for parent in (*candidate.parents, *resolved.parents)
            )
        except (OSError, RuntimeError):
            continue
        file_is_trusted = (
            stat.S_ISREG(file_status.st_mode)
            and file_status.st_uid == 0
            and file_status.st_mode & 0o022 == 0
            and file_status.st_mode & 0o111 != 0
        )
        parents_are_trusted = all(
            stat.S_ISDIR(parent_status.st_mode)
            and parent_status.st_uid == 0
            and parent_status.st_mode & 0o022 == 0
            for parent_status in parent_statuses
        )
        if file_is_trusted and parents_are_trusted:
            return candidate
    return None


def require_trusted_system_command(command_name: str) -> str:
    command_path = resolve_trusted_system_command(command_name=command_name)
    if command_path is None:
        raise RuntimeError(f"Required trusted system command is unavailable: {command_name}")
    return str(command_path)


def authorize_privileged_commands() -> PrivilegePrefix:
    if os.geteuid() == 0:
        return ()
    sudo_path = resolve_trusted_system_command(command_name="sudo")
    if sudo_path is None:
        raise RuntimeError("Root privileges are required. Install sudo or run change-port as root.")
    result = subprocess.run((str(sudo_path), "-v"), check=False)
    if result.returncode != 0:
        raise RuntimeError("Unable to obtain root privileges with sudo; run `sudo -v`, then retry.")
    return (str(sudo_path),)


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
    command = (*privilege_prefix, require_trusted_system_command(command_name="tee"), str(path))
    result = subprocess.run(command, input=content, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return
    error_output = result.stderr.strip() or result.stdout.strip()
    suffix = f": {error_output}" if error_output != "" else f" (exit code {result.returncode})"
    raise RuntimeError(f"Failed to write {path}{suffix}")


def read_privileged_text(path: Path, privilege_prefix: PrivilegePrefix) -> str:
    return capture_checked_command(
        command=(*privilege_prefix, require_trusted_system_command(command_name="cat"), str(path)),
        failure_message=f"Failed to read {path}",
    )


def privileged_path_exists(path: Path, privilege_prefix: PrivilegePrefix) -> bool:
    result = run_command(
        (*privilege_prefix, require_trusted_system_command(command_name="test"), "-e", str(path))
    )
    return result.returncode == 0
