import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import (
    CleanOutcome,
    CommandCleanup,
    PathCleanup,
    Platform,
    ProjectCleanup,
    TargetScan,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_paths import removal_block_reason
from stackops.scripts.python.helpers.helpers_utils.clean_drive_plans import resolve_command
from stackops.scripts.python.helpers.helpers_utils.clean_drive_scan import requires_root, scan_target
from stackops.scripts.python.helpers.helpers_utils.clean_drive_usage import combine_usages, measure_path, reclaimable_bytes


def is_elevated() -> bool:
    if sys.platform == "win32":
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


def _run(*, command: tuple[str, ...], sudo: bool) -> str | None:
    resolved = resolve_command(command)
    completed = subprocess.run(("sudo", *resolved) if sudo else resolved, capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return None
    lines = (completed.stderr or completed.stdout).strip().splitlines()
    return f"""`{" ".join(command)}` failed: {lines[-1] if lines else f"exit code {completed.returncode}"}"""


def _delete(path: Path) -> list[str]:
    errors: list[str] = []

    def retry_writable(function: Callable[[str], object], failed_path: str, error: BaseException) -> None:
        if isinstance(error, FileNotFoundError):
            return
        if not isinstance(error, PermissionError):
            errors.append(f"""{failed_path}: {error}""")
            return
        try:
            os.chmod(os.path.dirname(failed_path), stat.S_IRWXU)
            os.chmod(failed_path, stat.S_IRWXU)
            function(failed_path)
        except OSError as retry_error:
            errors.append(f"""{failed_path}: {retry_error}""")

    try:
        if path.is_junction():
            path.rmdir()
        elif path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, onexc=retry_writable)
        else:
            path.unlink(missing_ok=True)
    except OSError as error:
        errors.append(f"""{path}: {error}""")
    return errors


def _remaining_bytes(scan: TargetScan) -> int | None:
    match scan.action:
        case CommandCleanup():
            return scan_target(target=scan.target, action=scan.action, project_entries={}).estimate.bytes
        case PathCleanup() | ProjectCleanup():
            return reclaimable_bytes(combine_usages(measure_path(measured.path) for measured in scan.paths))


def clean_target(*, scan: TargetScan, elevated: bool, platform: Platform) -> CleanOutcome:
    key = scan.target.key
    needs_sudo = requires_root(scan.action) and not elevated
    if needs_sudo and platform == "windows":
        return CleanOutcome(key=key, status="skipped", freed_bytes=None, message="needs an elevated (Administrator) terminal")
    match scan.action:
        case CommandCleanup():
            errors = [error for command in scan.commands if (error := _run(command=command, sudo=needs_sudo)) is not None]
        case PathCleanup() | ProjectCleanup():
            blocked = [reason for measured in scan.paths if (reason := removal_block_reason(measured.path)) is not None]
            if blocked:
                return CleanOutcome(key=key, status="failed", freed_bytes=None, message="; ".join(blocked))
            if needs_sudo:
                error = _run(command=("rm", "-rf", "--", *(str(measured.path) for measured in scan.paths)), sudo=True)
                errors = [] if error is None else [error]
            else:
                errors = [error for measured in scan.paths for error in _delete(measured.path)]
    remaining = _remaining_bytes(scan)
    before = scan.estimate.bytes
    freed = None if before is None or remaining is None else max(0, before - remaining)
    if not errors:
        return CleanOutcome(key=key, status="cleaned", freed_bytes=freed, message="done")
    summary = errors[0] if len(errors) == 1 else f"""{errors[0]} (+{len(errors) - 1} more errors)"""
    return CleanOutcome(key=key, status="partial" if freed is not None and freed > 0 else "failed", freed_bytes=freed, message=summary)
