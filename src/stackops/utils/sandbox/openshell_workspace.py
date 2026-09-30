import os
import subprocess
from pathlib import Path

from stackops.utils.sandbox.openshell_workspace_entries import (
    WorkspaceEntry,
    copy_workspace_entry,
    has_directory_ancestors,
    read_workspace_entries,
    read_workspace_entry,
)


def snapshot_workspace(*, directory: Path, destination: Path) -> None:
    probe = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
        stdin=subprocess.DEVNULL, capture_output=True, check=False,
    )
    if probe.returncode != 0 and any((parent / ".git").exists() for parent in (directory, *directory.parents)):
        probe.check_returncode()
    selected: set[Path] | None = None
    selected_files: set[Path] = set()
    if probe.returncode == 0 and probe.stdout.strip() == b"true":
        listing = subprocess.run(
            ["git", "-C", str(directory), "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "."],
            stdin=subprocess.DEVNULL, capture_output=True, check=True,
        )
        selected = set()
        for name in listing.stdout.split(b"\0"):
            if not name:
                continue
            relative = Path(os.fsdecode(name))
            selected_files.add(relative)
            selected.add(relative)
            selected.update(relative.parents)
    entries = read_workspace_entries(directory=directory, selected=selected, include_git=False)
    for relative, entry in entries.items():
        if entry.kind == "other":
            raise ValueError(f"""Cannot copy special workspace file into OpenShell: {relative}""")
    destination.mkdir(parents=True, exist_ok=False)
    ordered = sorted(entries, key=lambda path: (len(path.parts), str(path)))
    nested_workspaces = {
        relative for relative in selected_files
        if relative in entries and entries[relative].kind == "directory"
    }
    for relative in ordered:
        if any(ancestor in nested_workspaces for ancestor in relative.parents):
            continue
        entry = entries[relative]
        target = destination / relative
        if relative in nested_workspaces:
            snapshot_workspace(directory=directory / relative, destination=target)
        elif entry.kind == "directory":
            target.mkdir()
        else:
            copy_workspace_entry(source=directory / relative, destination=target)
    for relative in reversed(ordered):
        entry = entries[relative]
        if entry.kind == "directory":
            (destination / relative).chmod(entry.mode)


def merge_workspace(*, directory: Path, baseline: Path, result: Path) -> tuple[Path, ...]:
    original = read_workspace_entries(directory=baseline, selected=None, include_git=False)
    updated = read_workspace_entries(directory=result, selected=None, include_git=False)
    changed = sorted(
        (path for path in original.keys() | updated.keys() if original.get(path) != updated.get(path)),
        key=lambda path: (len(path.parts), str(path)),
    )
    conflicts: set[Path] = set()
    completed_subtrees: set[Path] = set()
    actions: list[tuple[Path, WorkspaceEntry | None, WorkspaceEntry | None]] = []
    for relative in changed:
        if any(ancestor in conflicts or ancestor in completed_subtrees for ancestor in relative.parents):
            continue
        if not has_directory_ancestors(directory=directory, relative=relative):
            conflicts.add(relative)
            continue
        before = original.get(relative)
        after = updated.get(relative)
        current = read_workspace_entry(directory / relative)
        if current == after:
            if before is not None and before.kind == "directory" and (after is None or after.kind != "directory"):
                completed_subtrees.add(relative)
            continue
        directory_transition = (
            before is not None and after is not None
            and (before.kind == "directory") != (after.kind == "directory")
        )
        if current != before or directory_transition or (after is not None and after.kind == "other"):
            conflicts.add(relative)
            continue
        if before is not None and before.kind == "directory" and after is None:
            expected_children = {
                path.relative_to(relative): entry
                for path, entry in original.items()
                if path != relative and path.is_relative_to(relative)
            }
            current_children = read_workspace_entries(directory=directory / relative, selected=None, include_git=True)
            if any(expected_children.get(path) != entry for path, entry in current_children.items()):
                conflicts.add(relative)
                continue
        actions.append((relative, before, after))

    actions.sort(key=lambda action: (
        action[2] is None,
        -len(action[0].parts) if action[2] is None else len(action[0].parts),
        str(action[0]),
    ))
    directory_modes: list[tuple[Path, WorkspaceEntry, WorkspaceEntry]] = []
    for relative, before, after in actions:
        if any(ancestor in conflicts for ancestor in relative.parents):
            continue
        if not has_directory_ancestors(directory=directory, relative=relative):
            conflicts.add(relative)
            continue
        target = directory / relative
        current = read_workspace_entry(target)
        if current == after:
            continue
        if current != before:
            conflicts.add(relative)
            continue
        if after is None:
            if before is not None and before.kind == "directory":
                if any(target.iterdir()):
                    conflicts.add(relative)
                else:
                    target.rmdir()
            else:
                target.unlink()
        elif after.kind == "directory":
            if current is None:
                target.mkdir()
                current = read_workspace_entry(target)
            if current is None:
                conflicts.add(relative)
            else:
                directory_modes.append((relative, current, after))
        else:
            copy_workspace_entry(source=result / relative, destination=target)
    for relative, before, after in sorted(directory_modes, key=lambda item: len(item[0].parts), reverse=True):
        if not has_directory_ancestors(directory=directory, relative=relative):
            conflicts.add(relative)
            continue
        target = directory / relative
        current = read_workspace_entry(target)
        if current == after:
            continue
        if current != before:
            conflicts.add(relative)
        else:
            target.chmod(after.mode, follow_symlinks=False)
    return tuple(sorted(conflicts))
