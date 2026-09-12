from pathlib import Path

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_documents import edit_cleanup_document
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupPlan, CleanupScope
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import capture_cleanup_snapshot
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory, HookRemoval


def build_cleanup_plan(*, inventory: HookInventory, scope: CleanupScope, match: str | None, home_directory: Path) -> CleanupPlan:
    if match is not None and not match.strip():
        raise ValueError("--match must contain a nonempty name, command, or source path")
    entries = tuple(
        entry for entry in inventory.entries
        if (scope == "all" or entry.origin == scope)
        and (match is None or match.casefold() in f"{entry.name} {entry.event} {entry.command} {entry.path}".casefold())
    )
    grouped: dict[Path, list[HookRemoval]] = {}
    for entry in entries:
        if entry.removal is None or entry.origin in ("admin", "system"):
            continue
        grouped.setdefault(entry.removal.path, []).append(entry.removal)
    directory_paths = {
        path for path, removals in grouped.items() if any(removal.format == "directory" for removal in removals)
    }
    entire_paths = {path for path, removals in grouped.items() if any(removal.format in ("file", "directory") for removal in removals)}
    blockers = [
        f"{diagnostic.path}: {diagnostic.message}" for diagnostic in inventory.diagnostics
        if diagnostic.severity == "error" and (scope == "all" or diagnostic.origin == scope)
        and not (
            diagnostic.origin in ("local", "global")
            and (diagnostic.path in entire_paths or any(diagnostic.path.is_relative_to(directory) for directory in directory_paths))
        )
    ]
    for entry in entries:
        if entry.origin in ("admin", "system") or (
            entry.removal is None and entry.path not in entire_paths
            and not any(entry.path.is_relative_to(directory) for directory in directory_paths)
        ):
            blockers.append(f"Read-only or externally managed resource: {entry.name} ({entry.path})")
    changes: list[CleanupChange] = []
    for path, raw_removals in grouped.items():
        if any(path != directory and path.is_relative_to(directory) for directory in directory_paths):
            continue
        try:
            snapshot = capture_cleanup_snapshot(path=path, home_directory=home_directory)
            removals = tuple(raw_removals)
            remove_entire_path = any(removal.format in ("file", "directory") for removal in removals)
            if remove_entire_path:
                replacement = None
            elif snapshot.directory or snapshot.links:
                raise ValueError(f"Cannot edit directory or symlink as structured configuration: {path}")
            else:
                replacement = edit_cleanup_document(original=snapshot.files[0].content, removals=removals)
            changes.append(CleanupChange(snapshot=snapshot, replacement=replacement))
        except (OSError, ValueError, yaml.YAMLError) as error:
            blockers.append(f"{path}: {error}")
    return CleanupPlan(entries=entries, changes=tuple(changes), blockers=tuple(dict.fromkeys(blockers)))
