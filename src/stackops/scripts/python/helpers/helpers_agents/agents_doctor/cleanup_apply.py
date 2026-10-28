import os
import shutil
import tempfile
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import (
    CleanupChange,
    CleanupEdit,
    CleanupPlan,
    CleanupRemoval,
    CleanupResult,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import read_editable_file, validate_removal_target


def apply_cleanup_plan(*, plan: CleanupPlan, home_directory: Path) -> CleanupResult:
    if plan.blockers:
        raise ValueError("Cleanup blocked; resolve the reported inspection errors or read-only resources first")
    for change in plan.changes:
        match change:
            case CleanupRemoval():
                validate_removal_target(path=change.path, home_directory=home_directory)
            case CleanupEdit():
                if read_editable_file(path=change.path, home_directory=home_directory) != (change.original, change.mode):
                    raise ValueError(f"Resource changed since inspection; run agents reset again: {change.path}")
    moved: list[tuple[CleanupChange, Path]] = []
    try:
        for change in plan.changes:
            staging_directory = Path(tempfile.mkdtemp(prefix=".stackops-depoison-", dir=change.path.parent))
            try:
                os.replace(change.path, staging_directory / "original")
            except OSError:
                staging_directory.rmdir()
                raise
            moved.append((change, staging_directory))
            if isinstance(change, CleanupEdit):
                descriptor = os.open(change.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, change.mode)
                with os.fdopen(descriptor, "wb") as target:
                    target.write(change.replacement)
                    target.flush()
                    os.fsync(target.fileno())
                change.path.chmod(change.mode)
    except (OSError, ValueError) as error:
        rollback_errors: list[str] = []
        for change, staging_directory in reversed(moved):
            try:
                os.replace(staging_directory / "original", change.path)
                staging_directory.rmdir()
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise ValueError(f"Cleanup failed ({error}); some changes could not be rolled back. Rollback errors: {details}") from error
        raise ValueError(f"Cleanup failed and changes were rolled back: {error}") from error
    for _change, staging_directory in moved:
        shutil.rmtree(staging_directory)
    return CleanupResult(changed_paths=tuple(change.path for change in plan.changes))
