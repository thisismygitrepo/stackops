import json
from collections import deque
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext


def permitted_resource_path(*, path: Path, home_directory: Path) -> bool:
    blocked_roots = (home_directory / "dotfiles", Path.home() / "dotfiles")
    candidate = path.expanduser().absolute()
    remaining = deque(candidate.parts[1:])
    current = Path(candidate.anchor)
    symlink_count = 0
    while remaining:
        component = remaining.popleft()
        if component == "..":
            current = current.parent
            continue
        current = current / component
        if any(current.is_relative_to(root) for root in blocked_roots):
            return False
        if current.is_symlink():
            symlink_count += 1
            if symlink_count > 40:
                return False
            target = current.readlink()
            current = Path(target.anchor) if target.is_absolute() else current.parent
            target_parts = target.parts[1:] if target.is_absolute() else target.parts
            remaining.extendleft(reversed(target_parts))
    return True


def permitted_hook_path(*, path: Path, context: DoctorContext) -> bool:
    return permitted_resource_path(path=path, home_directory=context.home_directory)


def read_hook_mapping(*, path: Path, context: DoctorContext) -> dict[str, object] | str | None:
    try:
        if not permitted_hook_path(path=path, context=context):
            return "Protected dotfiles path was excluded; hook coverage is incomplete."
        if not path.exists():
            return None
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        return str(error)
    if not isinstance(value, dict):
        return "Hook configuration root must be an object."
    return cast(dict[str, object], value)


def hook_directory_files(*, directory: Path, context: DoctorContext) -> tuple[Path, ...] | str:
    try:
        if not permitted_hook_path(path=directory, context=context):
            return "Protected dotfiles directory was excluded; hook coverage is incomplete."
        if not directory.exists():
            return ()
        return tuple(sorted(directory.iterdir()))
    except OSError as error:
        return str(error)
