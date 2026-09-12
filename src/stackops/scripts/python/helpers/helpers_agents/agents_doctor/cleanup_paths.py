import os
import stat
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupFile, CleanupSnapshot


def validate_cleanup_path(*, path: Path, home_directory: Path, allow_leaf_symlink: bool) -> None:
    forbidden = (home_directory / "dotfiles", Path.home() / "dotfiles")
    absolute = path.expanduser()
    if not absolute.is_absolute():
        absolute = Path.cwd() / absolute
    if ".." in absolute.parts:
        raise ValueError(f"Cleanup paths must not contain parent traversal: {path}")
    if any(absolute.is_relative_to(root) for root in forbidden):
        raise ValueError(f"Protected path cannot be inspected or changed: {path}")
    components = tuple(reversed(absolute.parents)) if allow_leaf_symlink else (*reversed(absolute.parents), absolute)
    for component in components:
        if component.is_symlink():
            raise ValueError(f"Symlink paths cannot be changed: {path}")


def capture_cleanup_snapshot(*, path: Path, home_directory: Path) -> CleanupSnapshot:
    validate_cleanup_path(path=path, home_directory=home_directory, allow_leaf_symlink=True)
    path_mode = path.lstat().st_mode
    if stat.S_ISLNK(path_mode):
        return CleanupSnapshot(path=path, directory=False, files=(), directories=(), links=((Path("."), os.readlink(path)),))
    if stat.S_ISREG(path_mode):
        if path.stat().st_nlink != 1:
            raise ValueError(f"Hard-linked files cannot be changed: {path}")
        file = CleanupFile(relative_path=Path("."), content=path.read_bytes(), mode=stat.S_IMODE(path_mode))
        return CleanupSnapshot(path=path, directory=False, files=(file,), directories=(), links=())
    if not stat.S_ISDIR(path_mode):
        raise ValueError(f"Only regular files and directories can be changed: {path}")
    files: list[CleanupFile] = []
    directories: list[tuple[Path, int]] = []
    links: list[tuple[Path, str]] = []
    pending = [path]
    while pending:
        directory = pending.pop()
        validate_cleanup_path(path=directory, home_directory=home_directory, allow_leaf_symlink=False)
        directories.append((directory.relative_to(path), stat.S_IMODE(directory.stat().st_mode)))
        for child in sorted(directory.iterdir()):
            validate_cleanup_path(path=child, home_directory=home_directory, allow_leaf_symlink=True)
            child_stat = child.lstat()
            if stat.S_ISLNK(child_stat.st_mode):
                links.append((child.relative_to(path), os.readlink(child)))
            elif stat.S_ISDIR(child_stat.st_mode):
                pending.append(child)
            elif stat.S_ISREG(child_stat.st_mode) and child_stat.st_nlink == 1:
                files.append(CleanupFile(child.relative_to(path), child.read_bytes(), stat.S_IMODE(child_stat.st_mode)))
            else:
                raise ValueError(f"Unsafe entry inside cleanup directory: {child}")
    return CleanupSnapshot(path=path, directory=True, files=tuple(files), directories=tuple(directories), links=tuple(links))
