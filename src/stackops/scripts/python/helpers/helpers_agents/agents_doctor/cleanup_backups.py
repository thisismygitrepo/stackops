from dataclasses import replace
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupSnapshot
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import capture_cleanup_snapshot


def write_cleanup_backup(*, snapshot: CleanupSnapshot, destination: Path, home_directory: Path) -> None:
    if snapshot.directory:
        for relative_path, _mode in snapshot.directories:
            (destination / relative_path).mkdir(parents=True, exist_ok=True)
    for file in snapshot.files:
        target = destination / file.relative_path if snapshot.directory else destination
        target.write_bytes(file.content)
        target.chmod(file.mode)
    for relative_path, target in snapshot.links:
        link = destination / relative_path if snapshot.directory else destination
        link.symlink_to(target)
    for relative_path, mode in reversed(snapshot.directories):
        (destination / relative_path).chmod(mode)
    if capture_cleanup_snapshot(path=destination, home_directory=home_directory) != replace(snapshot, path=destination):
        raise ValueError(f"Backup verification failed: {destination}")
