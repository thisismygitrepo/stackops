import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import WorkspaceId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import (
    IterRunManifest,
    current_herdr_session,
    load_iter_run_manifest,
    resolve_repo_root,
)


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
    *, cwd: Path, dry_run: bool, load_active_workspace_ids: Callable[[], frozenset[WorkspaceId]], report: Callable[[str], None]
) -> AgentopsCacheCleanResult:
    try:
        return _clean_agentops_cache(cwd=cwd, dry_run=dry_run, load_active_workspace_ids=load_active_workspace_ids, report=report)
    except OSError as error:
        raise RuntimeError(f"Failed to clean AgentOps iteration records: {error}") from error


def _clean_agentops_cache(
    *, cwd: Path, dry_run: bool, load_active_workspace_ids: Callable[[], frozenset[WorkspaceId]], report: Callable[[str], None]
) -> AgentopsCacheCleanResult:
    repo_root = resolve_repo_root(cwd=cwd)
    ai_path = repo_root.joinpath(".ai")
    agentops_path = ai_path.joinpath("agentops")
    iterations_path = agentops_path.joinpath("iterations")
    for path, label in ((ai_path, "AI directory"), (agentops_path, "AgentOps directory"), (iterations_path, "AgentOps iterations directory")):
        if path.is_symlink():
            raise RuntimeError(f"Refusing to clean symlinked {label}: {_format_repo_path(path=path, repo_root=repo_root)}")
        if not path.exists():
            report(f"No AgentOps iteration records found at {_format_repo_path(path=iterations_path, repo_root=repo_root)}.")
            return _empty_result(repo_root=repo_root, iterations_path=iterations_path, dry_run=dry_run)
        if not path.is_dir():
            raise RuntimeError(f"Refusing to clean non-directory {label}: {_format_repo_path(path=path, repo_root=repo_root)}")

    current_runs: list[tuple[Path, IterRunManifest]] = []
    unmanaged_paths: list[Path] = []
    for entry in sorted(iterations_path.iterdir(), key=lambda path: path.name):
        if entry.is_symlink():
            raise RuntimeError(f"Refusing to clean symlinked AgentOps iteration entry: {_format_repo_path(path=entry, repo_root=repo_root)}")
        if not entry.is_dir():
            unmanaged_paths.append(entry)
            continue
        manifest = load_iter_run_manifest(run_path=entry)
        if manifest is None or manifest.herdr_session != current_herdr_session():
            unmanaged_paths.append(entry)
        else:
            current_runs.append((entry, manifest))

    unmanaged_entries = tuple(unmanaged_paths)
    for unmanaged_entry in unmanaged_entries:
        report(f"Preserved non-current iteration entry {_format_repo_path(path=unmanaged_entry, repo_root=repo_root)}.")
    if len(current_runs) == 0:
        report(f"No inactive current AgentOps iteration runs found at {_format_repo_path(path=iterations_path, repo_root=repo_root)}.")
        return AgentopsCacheCleanResult(repo_root, iterations_path, (), (), unmanaged_entries, 0, dry_run)

    active_workspace_ids = load_active_workspace_ids()
    protected_run_paths: set[Path] = set()
    removal_candidates: list[tuple[Path, IterRunManifest]] = []
    for run_path, manifest in current_runs:
        if manifest.workspace_id in active_workspace_ids:
            protected_run_paths.add(run_path)
            report(
                f"Protected active iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} "
                f"(workspace {manifest.workspace_label} {manifest.workspace_id})."
            )
        else:
            removal_candidates.append((run_path, manifest))

    removed_runs: list[Path] = []
    removed_entries = 0
    for run_path, manifest in removal_candidates:
        if run_path.is_symlink() or not run_path.is_dir():
            raise RuntimeError(f"Refusing to clean changed AgentOps iteration entry: {_format_repo_path(path=run_path, repo_root=repo_root)}")
        run_entry_count = _count_path_entries(path=run_path)
        if dry_run:
            removed_runs.append(run_path)
            removed_entries += run_entry_count
            report(f"Would remove inactive iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} ({run_entry_count} path(s)).")
            continue

        refreshed_manifest = load_iter_run_manifest(run_path=run_path)
        if refreshed_manifest != manifest:
            raise RuntimeError(f"Refusing to clean changed AgentOps run manifest: {_format_repo_path(path=run_path, repo_root=repo_root)}")
        if manifest.workspace_id in load_active_workspace_ids():
            protected_run_paths.add(run_path)
            report(
                f"Protected newly active iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} "
                f"(workspace {manifest.workspace_label} {manifest.workspace_id})."
            )
            continue
        shutil.rmtree(run_path)
        removed_runs.append(run_path)
        removed_entries += run_entry_count
        report(f"Removed inactive iteration run {_format_repo_path(path=run_path, repo_root=repo_root)} ({run_entry_count} path(s)).")

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
    return AgentopsCacheCleanResult(repo_root, iterations_path, (), (), (), 0, dry_run)


def _count_path_entries(*, path: Path) -> int:
    return 1 + sum(1 for _path in path.rglob("*"))


def _format_repo_path(*, path: Path, repo_root: Path) -> str:
    try:
        relative_path = path.relative_to(repo_root)
    except ValueError:
        return path.as_posix()
    return f"./{relative_path.as_posix()}"
