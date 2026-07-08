import filecmp
from pathlib import Path
import shutil
from typing import Literal, TypeAlias
from uuid import uuid4


TargetConflictAction: TypeAlias = Literal["throw-error", "overwrite-target", "merge-target"]


class TargetConflictError(RuntimeError):
    pass


def _exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _is_directory(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def _leaf_paths_equal(source: Path, target: Path) -> bool:
    if source.is_symlink() or target.is_symlink():
        return source.is_symlink() and target.is_symlink() and source.readlink() == target.readlink()
    if source.is_file() and target.is_file():
        return filecmp.cmp(source, target, shallow=False)
    return False


def _find_conflicts(source: Path, target: Path, relative_path: Path) -> list[Path]:
    if not _exists(target):
        return []
    if _is_directory(source) and _is_directory(target):
        conflicts: list[Path] = []
        for source_child in source.iterdir():
            child_relative_path = relative_path / source_child.name
            conflicts.extend(_find_conflicts(source_child, target / source_child.name, child_relative_path))
        return conflicts
    if _leaf_paths_equal(source, target):
        return []
    return [relative_path]


def _delete_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _replace_path(staged_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not _exists(target_path):
        staged_path.rename(target_path)
        return

    backup_path = target_path.with_name(f".{target_path.name}.stackops-replaced-{uuid4().hex}")
    target_path.rename(backup_path)
    try:
        staged_path.rename(target_path)
    except BaseException:
        backup_path.rename(target_path)
        raise
    _delete_path(backup_path)


def _merge_path(staged_path: Path, target_path: Path) -> None:
    if not _exists(target_path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.rename(target_path)
        return
    if _is_directory(staged_path) and _is_directory(target_path):
        for staged_child in tuple(staged_path.iterdir()):
            _merge_path(staged_child, target_path / staged_child.name)
        return
    _replace_path(staged_path, target_path)


def _format_conflict_path(relative_path: Path) -> str:
    return "<target root>" if relative_path == Path() else relative_path.as_posix()


def apply_target_conflict_action(
    *,
    staged_path: Path,
    target_path: Path,
    on_conflict: TargetConflictAction,
) -> Path:
    if not _exists(staged_path):
        raise FileNotFoundError(f"Staged transfer path does not exist: {staged_path}")

    match on_conflict:
        case "throw-error":
            conflicts = _find_conflicts(staged_path, target_path, Path())
            if conflicts:
                conflict_lines = "\n".join(f"- {_format_conflict_path(path)}" for path in conflicts)
                raise TargetConflictError(
                    f"Refusing to modify target because {len(conflicts)} conflicting path(s) differ:\n{conflict_lines}\n"
                    "Use --on-conflict overwrite-target or --on-conflict merge-target to replace them."
                )
            _merge_path(staged_path, target_path)
        case "overwrite-target":
            _replace_path(staged_path, target_path)
        case "merge-target":
            _merge_path(staged_path, target_path)
    return target_path
