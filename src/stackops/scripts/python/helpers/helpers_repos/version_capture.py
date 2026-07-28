import concurrent.futures
import os
from pathlib import Path
from typing import cast

from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.remote import Remote
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.discovery import repository_candidates
from stackops.scripts.python.helpers.helpers_repos.version_models import DeclaredVersion, RemoteBranchSnapshot, RemoteSnapshot, RepositorySnapshot


class VersionOperationError(RuntimeError):
    pass


def _parse_remote_branches(output: str, repository_path: Path, remote_name: str) -> list[RemoteBranchSnapshot]:
    branches: list[RemoteBranchSnapshot] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[1].startswith("refs/heads/"):
            raise VersionOperationError(f"Unexpected ls-remote output for {repository_path} remote {remote_name!r}: {line!r}")
        commit, reference = fields
        if len(commit) not in {40, 64} or any(character not in "0123456789abcdef" for character in commit.lower()):
            raise VersionOperationError(f"Remote {remote_name!r} returned an invalid object ID for {repository_path}: {commit!r}")
        branches.append({"name": reference.removeprefix("refs/heads/"), "commit": commit.lower()})
    return sorted(branches, key=lambda branch: branch["name"])


def _capture_remote(repository: Repo, repository_path: Path, remote: Remote) -> RemoteSnapshot:
    urls = sorted({str(url) for url in remote.urls})
    if not urls:
        raise VersionOperationError(f"Remote {remote.name!r} has no URL in {repository_path}")
    try:
        with repository.git.custom_environment(GIT_TERMINAL_PROMPT="0"):
            output = cast(str, repository.git.ls_remote("--heads", remote.name))
    except GitCommandError as error:
        raise VersionOperationError(f"Failed to read remote {remote.name!r} for {repository_path}: {error}") from error
    return {
        "name": remote.name,
        "urls": urls,
        "branches": _parse_remote_branches(output=output, repository_path=repository_path, remote_name=remote.name),
    }


def capture_repository(repos_root: Path, repository_path: Path) -> RepositorySnapshot:
    try:
        repository = Repo(repository_path, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError) as error:
        raise VersionOperationError(f"Not a Git repository: {repository_path}") from error
    if repository.bare or repository.working_tree_dir is None:
        raise VersionOperationError(f"Bare repositories cannot be versioned: {repository_path}")
    try:
        commit = repository.head.commit.hexsha.lower()
    except ValueError as error:
        raise VersionOperationError(f"Repository has no commits: {repository_path}") from error
    branch = None if repository.head.is_detached else repository.active_branch.name
    resolved_root = repos_root.expanduser().absolute().resolve()
    resolved_repository_path = Path(repository.working_tree_dir).absolute().resolve()
    try:
        relative_path = resolved_repository_path.relative_to(resolved_root).as_posix()
    except ValueError as error:
        raise VersionOperationError(f"Repository is outside workspace {resolved_root}: {resolved_repository_path}") from error
    remotes = [
        _capture_remote(repository=repository, repository_path=resolved_repository_path, remote=remote)
        for remote in sorted(repository.remotes, key=lambda item: item.name)
    ]
    return {
        "path": relative_path,
        "branch": branch,
        "commit": commit,
        "isDirty": repository.is_dirty(untracked_files=True, submodules=True),
        "remotes": remotes,
    }


def _capture_candidate(repos_root: Path, repository_path: Path) -> RepositorySnapshot | None:
    try:
        Repo(repository_path, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None
    return capture_repository(repos_root=repos_root, repository_path=repository_path)


def capture_declared_version(repos_root: Path, version: str, message: str, recursive: bool) -> DeclaredVersion:
    normalized_version = version.strip()
    normalized_message = message.strip()
    if not normalized_version:
        raise VersionOperationError("Version identifier must not be empty")
    if not normalized_message:
        raise VersionOperationError("Version message must not be empty")
    candidates = repository_candidates(repos_root=repos_root, recursive=recursive)
    max_workers = min(32, (os.cpu_count() or 1) * 5, len(candidates) or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_capture_candidate, repos_root, path) for path in candidates]
        snapshots = [snapshot for future in concurrent.futures.as_completed(futures) if (snapshot := future.result()) is not None]
    snapshots.sort(key=lambda snapshot: snapshot["path"])
    if not snapshots:
        raise VersionOperationError(f"No Git repositories found under {repos_root}")
    return {"version": normalized_version, "message": normalized_message, "repositories": snapshots}
