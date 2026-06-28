import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.accessories import get_repo_root


@dataclass(frozen=True, slots=True)
class AgentopsCacheCleanResult:
    repo_root: Path
    cache_path: Path
    removed: bool
    removed_entries: int


def clean_agentops_cache(*, cwd: Path, report: Callable[[str], None]) -> AgentopsCacheCleanResult:
    repo_root = _resolve_repo_root(cwd=cwd)
    cache_path = repo_root.joinpath(".ai", "agentops")
    _ensure_path_under_ai(path=cache_path, repo_root=repo_root)
    if not cache_path.exists():
        report(f"No AgentOps cache found at {_format_repo_path(path=cache_path, repo_root=repo_root)}.")
        return AgentopsCacheCleanResult(repo_root=repo_root, cache_path=cache_path, removed=False, removed_entries=0)

    removed_entries = _count_path_entries(path=cache_path)
    if cache_path.is_dir() and not cache_path.is_symlink():
        shutil.rmtree(cache_path)
    else:
        cache_path.unlink()
    report(f"Removed AgentOps cache at {_format_repo_path(path=cache_path, repo_root=repo_root)} ({removed_entries} path(s)).")
    return AgentopsCacheCleanResult(
        repo_root=repo_root,
        cache_path=cache_path,
        removed=True,
        removed_entries=removed_entries,
    )


def _resolve_repo_root(*, cwd: Path) -> Path:
    repo_root = get_repo_root(cwd)
    if repo_root is None:
        return cwd.resolve(strict=False)
    return repo_root.resolve(strict=False)


def _ensure_path_under_ai(*, path: Path, repo_root: Path) -> None:
    resolved_path = path.resolve(strict=False)
    resolved_ai = repo_root.joinpath(".ai").resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_ai)
    except ValueError as error:
        raise RuntimeError(f"Refusing to clean a path outside .ai: {resolved_path}") from error


def _count_path_entries(*, path: Path) -> int:
    if path.is_dir() and not path.is_symlink():
        return 1 + sum(1 for _path in path.rglob("*"))
    return 1


def _format_repo_path(*, path: Path, repo_root: Path) -> str:
    try:
        relative_path = path.relative_to(repo_root)
    except ValueError:
        return path.as_posix()
    return f"./{relative_path.as_posix()}"
