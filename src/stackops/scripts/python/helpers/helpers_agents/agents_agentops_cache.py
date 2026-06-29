import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.accessories import get_repo_root


@dataclass(frozen=True, slots=True)
class AgentopsCacheCleanResult:
    repo_root: Path
    iterations_path: Path
    removed_runs: tuple[Path, ...]
    protected_runs: tuple[Path, ...]
    unmanaged_entries: tuple[Path, ...]
    removed_entries: int
    dry_run: bool

    @property
    def removed(self) -> bool:
        return not self.dry_run and len(self.removed_runs) > 0


def clean_agentops_cache(
    *,
    cwd: Path,
    dry_run: bool,
    load_active_iter_workspace_labels: Callable[[], frozenset[str]],
    report: Callable[[str], None],
) -> AgentopsCacheCleanResult:
    try:
        return _clean_agentops_cache(
            cwd=cwd,
            dry_run=dry_run,
            load_active_iter_workspace_labels=load_active_iter_workspace_labels,
            report=report,
        )
    except OSError as error:
        raise RuntimeError(f"Failed to clean AgentOps iteration records: {error}") from error


def _clean_agentops_cache(
    *,
    cwd: Path,
    dry_run: bool,
    load_active_iter_workspace_labels: Callable[[], frozenset[str]],
    report: Callable[[str], None],
) -> AgentopsCacheCleanResult:
    repo_root = _resolve_repo_root(cwd=cwd)
    ai_path = repo_root.joinpath(".ai")
    agentops_path = ai_path.joinpath("agentops")
    iterations_path = agentops_path.joinpath("iterations")

    for path, label in (
        (ai_path, "AI directory"),
        (agentops_path, "AgentOps directory"),
        (iterations_path, "AgentOps iterations directory"),
    ):
        if path.is_symlink():
            raise RuntimeError(f"Refusing to clean symlinked {label}: {_format_repo_path(path=path, repo_root=repo_root)}")
        if not path.exists():
            report(f"No AgentOps iteration records found at {_format_repo_path(path=iterations_path, repo_root=repo_root)}.")
            return _empty_result(repo_root=repo_root, iterations_path=iterations_path, dry_run=dry_run)
        if not path.is_dir():
            raise RuntimeError(f"Refusing to clean non-directory {label}: {_format_repo_path(path=path, repo_root=repo_root)}")

    run_paths: list[Path] = []
    unmanaged_paths: list[Path] = []
    for entry in sorted(iterations_path.iterdir(), key=lambda path: path.name):
        if entry.is_symlink():
            raise RuntimeError(
                f"Refusing to clean symlinked AgentOps iteration entry: {_format_repo_path(path=entry, repo_root=repo_root)}"
            )
        if entry.is_dir():
            run_paths.append(entry)
        else:
            unmanaged_paths.append(entry)

    unmanaged_entries = tuple(unmanaged_paths)
    for unmanaged_entry in unmanaged_entries:
        report(f"Preserved unmanaged iteration entry {_format_repo_path(path=unmanaged_entry, repo_root=repo_root)}.")

    if len(run_paths) == 0:
        report(f"No inactive AgentOps iteration runs found at {_format_repo_path(path=iterations_path, repo_root=repo_root)}.")
        return AgentopsCacheCleanResult(
            repo_root=repo_root,
            iterations_path=iterations_path,
            removed_runs=(),
            protected_runs=(),
            unmanaged_entries=unmanaged_entries,
            removed_entries=0,
            dry_run=dry_run,
        )

    active_workspace_labels = load_active_iter_workspace_labels()
    protected_run_paths: set[Path] = set()
    removal_candidates: list[Path] = []
    for run_path in run_paths:
        workspace_label = _workspace_label_for_run(run_path=run_path)
        if workspace_label in active_workspace_labels:
            protected_run_paths.add(run_path)
            report(
                f"Protected active iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} "
                f"(workspace {workspace_label})."
            )
        else:
            removal_candidates.append(run_path)

    removed_runs: list[Path] = []
    removed_entries = 0
    for run_path in removal_candidates:
        if run_path.is_symlink() or not run_path.is_dir():
            raise RuntimeError(
                f"Refusing to clean changed AgentOps iteration entry: {_format_repo_path(path=run_path, repo_root=repo_root)}"
            )
        run_entry_count = _count_path_entries(path=run_path)
        if dry_run:
            removed_runs.append(run_path)
            removed_entries += run_entry_count
            report(
                f"Would remove inactive iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} "
                f"({run_entry_count} path(s))."
            )
            continue

        refreshed_active_workspace_labels = load_active_iter_workspace_labels()
        workspace_label = _workspace_label_for_run(run_path=run_path)
        if workspace_label in refreshed_active_workspace_labels:
            protected_run_paths.add(run_path)
            report(
                f"Protected newly active iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} "
                f"(workspace {workspace_label})."
            )
            continue

        shutil.rmtree(run_path)
        removed_runs.append(run_path)
        removed_entries += run_entry_count
        report(
            f"Removed inactive iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} "
            f"({run_entry_count} path(s))."
        )

    return AgentopsCacheCleanResult(
        repo_root=repo_root,
        iterations_path=iterations_path,
        removed_runs=tuple(removed_runs),
        protected_runs=tuple(sorted(protected_run_paths, key=lambda path: path.name)),
        unmanaged_entries=unmanaged_entries,
        removed_entries=removed_entries,
        dry_run=dry_run,
    )


def _empty_result(*, repo_root: Path, iterations_path: Path, dry_run: bool) -> AgentopsCacheCleanResult:
    return AgentopsCacheCleanResult(
        repo_root=repo_root,
        iterations_path=iterations_path,
        removed_runs=(),
        protected_runs=(),
        unmanaged_entries=(),
        removed_entries=0,
        dry_run=dry_run,
    )


def _resolve_repo_root(*, cwd: Path) -> Path:
    repo_root = get_repo_root(cwd)
    if repo_root is None:
        return cwd.resolve(strict=False)
    return repo_root.resolve(strict=False)


def _workspace_label_for_run(*, run_path: Path) -> str:
    return f"iter-{run_path.name}"


def _count_path_entries(*, path: Path) -> int:
    return 1 + sum(1 for _path in path.rglob("*"))


def _format_repo_path(*, path: Path, repo_root: Path) -> str:
    try:
        relative_path = path.relative_to(repo_root)
    except ValueError:
        return path.as_posix()
    return f"./{relative_path.as_posix()}"
