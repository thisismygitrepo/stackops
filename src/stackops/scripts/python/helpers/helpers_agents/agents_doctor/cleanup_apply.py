import json
import os
import shutil
import tempfile
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_backups import write_cleanup_backup
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupPlan, CleanupResult
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import capture_cleanup_snapshot, validate_cleanup_path


def apply_cleanup_plan(*, plan: CleanupPlan, backup_root: Path, home_directory: Path) -> CleanupResult:
    if plan.blockers:
        raise ValueError("Cleanup blocked; resolve the reported inspection errors or read-only resources first")
    if not plan.changes:
        return CleanupResult(changed_paths=(), backup_directory=None)
    validate_cleanup_path(path=backup_root, home_directory=home_directory, allow_leaf_symlink=False)
    for change in plan.changes:
        path = change.snapshot.path
        if backup_root == path or backup_root.is_relative_to(path):
            raise ValueError(f"Backup directory cannot be inside a cleanup target: {path}")
        if capture_cleanup_snapshot(path=path, home_directory=home_directory) != change.snapshot:
            raise ValueError(f"Configuration changed since inspection; run depoison again: {path}")
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_directory = Path(tempfile.mkdtemp(prefix="run-", dir=backup_root))
    destinations = tuple(backup_directory / f"{index:04d}-{change.snapshot.path.name}" for index, change in enumerate(plan.changes))
    manifest = [
        {"original": str(change.snapshot.path), "backup": str(destination), "action": "remove" if change.replacement is None else "edit"}
        for change, destination in zip(plan.changes, destinations, strict=True)
    ]
    (backup_directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for change, destination in zip(plan.changes, destinations, strict=True):
        write_cleanup_backup(snapshot=change.snapshot, destination=destination, home_directory=home_directory)
    moved: list[tuple[CleanupChange, Path]] = []
    try:
        for change in plan.changes:
            path = change.snapshot.path
            if capture_cleanup_snapshot(path=path, home_directory=home_directory) != change.snapshot:
                raise ValueError(f"Configuration changed during cleanup: {path}")
            staging_directory = Path(tempfile.mkdtemp(prefix=".stackops-depoison-", dir=path.parent))
            try:
                os.replace(path, staging_directory / "original")
            except OSError:
                staging_directory.rmdir()
                raise
            moved.append((change, staging_directory))
            if change.replacement is not None:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, change.snapshot.files[0].mode)
                with os.fdopen(descriptor, "wb") as target:
                    target.write(change.replacement)
                    target.flush()
                    os.fsync(target.fileno())
                path.chmod(change.snapshot.files[0].mode)
    except (OSError, ValueError) as error:
        rollback_errors: list[str] = []
        for change, staging_directory in reversed(moved):
            try:
                os.replace(staging_directory / "original", change.snapshot.path)
                staging_directory.rmdir()
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise ValueError(f"Cleanup failed ({error}); restore backups from {backup_directory}. Rollback errors: {details}") from error
        raise ValueError(f"Cleanup failed and changes were rolled back: {error}") from error
    for _change, staging_directory in moved:
        shutil.rmtree(staging_directory)
    return CleanupResult(changed_paths=tuple(change.snapshot.path for change in plan.changes), backup_directory=backup_directory)
