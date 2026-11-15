import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import PROJECT_SCAN_PRUNED_DIRECTORIES, PROJECT_SCAN_PRUNED_HOME_DIRECTORIES
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import ProjectCleanup


def find_project_entries(*, roots: tuple[Path, ...], cleanups: dict[str, ProjectCleanup]) -> dict[str, list[Path]]:
    candidates: dict[str, list[tuple[str, ProjectCleanup]]] = {}
    for key, cleanup in cleanups.items():
        for name in cleanup.directory_names:
            candidates.setdefault(name, []).append((key, cleanup))
    found: dict[str, list[Path]] = {key: [] for key in cleanups}
    home = Path.home()
    for root in roots:
        root_device = root.stat().st_dev
        pending = [root]
        while pending:
            current = pending.pop()
            try:
                with os.scandir(current) as scanned:
                    entries = sorted(scanned, key=lambda entry: entry.name)
            except (PermissionError, FileNotFoundError):
                continue
            for entry in entries:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                entry_path = Path(entry.path)
                matched_key = next((
                    key for key, cleanup in candidates.get(entry.name, [])
                    if cleanup.marker is None
                    or (cleanup.marker.relation == "sibling" and (current / cleanup.marker.name).exists())
                    or (cleanup.marker.relation == "child" and (entry_path / cleanup.marker.name).exists())
                ), None)
                if matched_key is not None:
                    found[matched_key].append(entry_path)
                    continue
                pruned = (
                    entry.name.startswith(".") or entry.name in PROJECT_SCAN_PRUNED_DIRECTORIES
                    or (current == home and entry.name in PROJECT_SCAN_PRUNED_HOME_DIRECTORIES)
                )
                if not pruned and entry.stat(follow_symlinks=False).st_dev == root_device:
                    pending.append(entry_path)
    return found
