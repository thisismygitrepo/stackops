from pathlib import Path

from stackops.scripts.python.helpers.helpers_repos.version_models import RepositorySnapshot


def resolve_workspace(directory: str | None) -> Path:
    workspace = Path.cwd() if directory is None else Path(directory).expanduser()
    resolved_workspace = workspace.absolute().resolve()
    if not resolved_workspace.exists():
        raise ValueError(f"Workspace directory does not exist: {resolved_workspace}")
    if not resolved_workspace.is_dir():
        raise ValueError(f"Workspace path is not a directory: {resolved_workspace}")
    return resolved_workspace


def snapshot_repository_path(repos_root: Path, snapshot: RepositorySnapshot) -> Path:
    resolved_root = repos_root.expanduser().absolute().resolve()
    repository_path = resolved_root.joinpath(snapshot["path"]).resolve()
    try:
        repository_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"Repository path escapes workspace: {snapshot['path']}") from error
    return repository_path
