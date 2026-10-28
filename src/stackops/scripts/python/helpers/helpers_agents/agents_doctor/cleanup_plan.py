from pathlib import Path

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_documents import edit_cleanup_document
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupEdit, CleanupPlan, CleanupRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_scope import CleanupScope
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_paths import read_editable_file, validate_removal_target
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants import CLEANUP_ORIGIN_LABELS
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory, HookRemoval


def build_cleanup_plan(*, inventory: HookInventory, scope: CleanupScope, match: str | None, home_directory: Path) -> CleanupPlan:
    if match is not None and not match.strip():
        raise ValueError("--match must contain a nonempty name, command, or source path")
    entries = tuple(
        entry for entry in inventory.entries
        if (scope == "all" or CLEANUP_ORIGIN_LABELS[entry.origin] == scope)
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
        if diagnostic.severity == "error" and (scope == "all" or CLEANUP_ORIGIN_LABELS[diagnostic.origin] == scope)
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
    targets = tuple(
        (path, removals) for path, removals in grouped.items()
        if not any(path != directory and path.is_relative_to(directory) for directory in directory_paths)
    )
    for path, removals in targets:
        try:
            if path in entire_paths:
                validate_removal_target(path=path, home_directory=home_directory)
                changes.append(CleanupRemoval(path=path))
            else:
                original, mode = read_editable_file(path=path, home_directory=home_directory)
                replacement = edit_cleanup_document(original=original, removals=tuple(removals))
                changes.append(CleanupEdit(path=path, original=original, mode=mode, replacement=replacement))
        except (OSError, ValueError, yaml.YAMLError) as error:
            blockers.append(f"{path}: {error}")
    return CleanupPlan(entries=entries, changes=tuple(changes), blockers=tuple(dict.fromkeys(blockers)))
