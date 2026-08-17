import os
from pathlib import Path
import platform
import shutil


def require_tree_without_filesystem_boundaries(*, directory: Path, include_root: bool, excluded_root_directory_names: frozenset[str]) -> None:
    mount_points = _linux_mount_points()
    compare_resolved_mount_paths = len(mount_points) > 0 and directory.resolve(strict=False) != directory.absolute()
    pending_directories = [directory]
    while len(pending_directories) > 0:
        current_directory = pending_directories.pop()
        try:
            if (include_root or current_directory != directory) and _is_filesystem_boundary(
                path=current_directory, linux_mount_points=mount_points, compare_resolved_mount_paths=compare_resolved_mount_paths
            ):
                raise RuntimeError(f"""Browser profile operation refuses filesystem boundary: {current_directory}""")
            with os.scandir(current_directory) as entries:
                for entry in entries:
                    if current_directory == directory and entry.name in excluded_root_directory_names:
                        continue
                    entry_path = Path(entry.path)
                    if entry.is_symlink():
                        continue
                    if _is_filesystem_boundary(
                        path=entry_path, linux_mount_points=mount_points, compare_resolved_mount_paths=compare_resolved_mount_paths
                    ):
                        raise RuntimeError(f"""Browser profile operation refuses filesystem boundary: {entry_path}""")
                    if entry.is_dir(follow_symlinks=False):
                        pending_directories.append(entry_path)
        except OSError as error:
            raise RuntimeError(f"""Could not inspect browser profile directory {current_directory}: {error}""") from error


def remove_owned_profile_directories(*, directories: tuple[Path, ...]) -> tuple[str, ...]:
    cleanup_failures: list[str] = []
    for directory in reversed(directories):
        try:
            if directory.is_junction():
                directory.rmdir()
            elif directory.is_dir() and not directory.is_symlink():
                shutil.rmtree(directory)
            elif directory.exists() or directory.is_symlink():
                directory.unlink()
        except OSError as error:
            cleanup_failures.append(f"""{directory}: {error}""")
    return tuple(cleanup_failures)


def path_is_filesystem_boundary(*, path: Path) -> bool:
    mount_points = _linux_mount_points()
    compare_resolved_mount_paths = len(mount_points) > 0 and path.resolve(strict=False) != path.absolute()
    return _is_filesystem_boundary(path=path, linux_mount_points=mount_points, compare_resolved_mount_paths=compare_resolved_mount_paths)


def copy_directory_tree_excluding(*, source_directory: Path, destination_directory: Path, excluded_root_directory_names: frozenset[str]) -> None:
    def ignored_root_directories(current_source: str, directory_names: list[str]) -> set[str]:
        if Path(current_source) != source_directory:
            return set()
        return set(directory_names).intersection(excluded_root_directory_names)

    shutil.copytree(source_directory, destination_directory, symlinks=True, dirs_exist_ok=True, ignore=ignored_root_directories)


def directory_size_bytes(*, directory: Path, excluded_root_directory_names: frozenset[str]) -> int:
    size_bytes = 0
    mount_points = _linux_mount_points()
    compare_resolved_mount_paths = len(mount_points) > 0 and directory.resolve(strict=False) != directory.absolute()
    pending_directories = [directory]
    while len(pending_directories) > 0:
        current_directory = pending_directories.pop()
        try:
            with os.scandir(current_directory) as entries:
                for entry in entries:
                    if current_directory == directory and entry.name in excluded_root_directory_names:
                        continue
                    entry_path = Path(entry.path)
                    if entry.is_symlink() or _is_filesystem_boundary(
                        path=entry_path, linux_mount_points=mount_points, compare_resolved_mount_paths=compare_resolved_mount_paths
                    ):
                        size_bytes += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        pending_directories.append(entry_path)
                    elif entry.is_file(follow_symlinks=False):
                        size_bytes += entry.stat(follow_symlinks=False).st_size
        except OSError as error:
            raise RuntimeError(f"""Could not measure browser profile directory {current_directory}: {error}""") from error
    return size_bytes


def _linux_mount_points() -> frozenset[Path]:
    if platform.system() != "Linux":
        return frozenset()
    mount_info_path = Path("/proc/self/mountinfo")
    try:
        mount_info_lines = mount_info_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(f"""Could not inspect Linux filesystem boundaries at {mount_info_path}: {error}""") from error
    mount_points: set[Path] = set()
    for line in mount_info_lines:
        fields = line.split()
        if len(fields) < 5:
            raise RuntimeError(f"""Invalid Linux mount information in {mount_info_path}: {line}""")
        decoded_mount_point = fields[4].replace(r"\040", " ").replace(r"\011", "\t").replace(r"\012", "\n").replace(r"\134", "\\")
        mount_points.add(Path(decoded_mount_point))
    return frozenset(mount_points)


def _is_filesystem_boundary(*, path: Path, linux_mount_points: frozenset[Path], compare_resolved_mount_paths: bool) -> bool:
    if path.is_junction() or path.is_mount() or path in linux_mount_points:
        return True
    return compare_resolved_mount_paths and path.resolve(strict=False) in linux_mount_points
