import stat
from pathlib import Path


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


def validate_removal_target(*, path: Path, home_directory: Path) -> None:
    validate_cleanup_path(path=path, home_directory=home_directory, allow_leaf_symlink=True)
    mode = path.lstat().st_mode
    if not (stat.S_ISLNK(mode) or stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise ValueError(f"Only regular files, directories, and symlinks can be removed: {path}")


def read_editable_file(*, path: Path, home_directory: Path) -> tuple[bytes, int]:
    validate_cleanup_path(path=path, home_directory=home_directory, allow_leaf_symlink=False)
    path_stat = path.lstat()
    if not stat.S_ISREG(path_stat.st_mode):
        raise ValueError(f"Only regular files can be edited as structured configuration: {path}")
    if path_stat.st_nlink != 1:
        raise ValueError(f"Hard-linked configuration cannot be edited: {path}")
    return path.read_bytes(), stat.S_IMODE(path_stat.st_mode)
