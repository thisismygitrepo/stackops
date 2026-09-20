import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


def _replacement_repository_head(repo_root: Path) -> str | None:
    from git.repo import Repo

    git_root = repo_root.joinpath(".git")
    if not git_root.is_dir(follow_symlinks=False):
        raise RuntimeError(f"Replacement requires a standalone Git repository: {repo_root}")
    with Repo(repo_root, search_parent_directories=False) as repo:
        if Path(repo.working_dir).resolve() != repo_root.resolve() or Path(repo.common_dir).resolve() != git_root.resolve():
            raise RuntimeError(f"Replacement repository refers to external Git metadata or a different worktree: {repo_root}")
        if repo.is_dirty(untracked_files=True):
            raise RuntimeError(f"Replacement repository has uncommitted changes: {repo_root}")
        return repo.head.commit.hexsha if repo.head.is_valid() else None


def overwrite_local_with_remote(repo_local_root: Path, repo_remote_root: Path) -> None:
    from rich.console import Console

    repo_local_root = repo_local_root.expanduser().absolute()
    repo_remote_root = repo_remote_root.expanduser().absolute()
    local_resolved = repo_local_root.resolve()
    remote_resolved = repo_remote_root.resolve()
    if local_resolved == Path.home().resolve() or local_resolved.parent == local_resolved:
        raise RuntimeError("Refusing to replace the home directory or a filesystem root as a repository.")
    if repo_local_root.is_symlink() or repo_remote_root.is_symlink():
        raise RuntimeError("Repository replacement requires directories, not symbolic links.")
    if not repo_local_root.is_dir() or not repo_remote_root.is_dir():
        raise FileNotFoundError("Both the local and downloaded repository directories must exist before replacement.")
    if local_resolved.is_relative_to(remote_resolved) or remote_resolved.is_relative_to(local_resolved):
        raise RuntimeError("The local and downloaded repository directories must not overlap.")

    recovery_root = Path(tempfile.mkdtemp(prefix=f".{repo_local_root.name}.stackops-", dir=repo_local_root.parent))
    staged_root = recovery_root.joinpath("incoming")
    backup_root = recovery_root.joinpath("backup")
    console = Console()
    console.print(
        f"Repository replacement recovery directory: {recovery_root}\nDownloaded copy retained: {repo_remote_root}", markup=False
    )
    try:
        shutil.copytree(repo_remote_root, staged_root, symlinks=True)
        expected_head = _replacement_repository_head(repo_root=staged_root)
    except Exception as error:
        raise RuntimeError(
            f"Could not stage and validate the replacement. The live repository is unchanged. "
            f"Downloaded copy: {repo_remote_root}. Staging directory: {staged_root}. {error}"
        ) from error

    os.chdir(repo_local_root.parent)
    if platform.system() == "Windows":
        gpg_home = subprocess.run(
            ["gpgconf", "--list-dirs", "homedir"], check=True, capture_output=True, text=True
        ).stdout.strip()
        gpg_keybox_path = Path(gpg_home).joinpath("public-keys.d", "pubring.db")
        if gpg_keybox_path.resolve().is_relative_to(local_resolved):
            subprocess.run(["gpgconf", "--homedir", gpg_home, "--kill", "all"], check=True)

    try:
        repo_local_root.rename(backup_root)
    except OSError as error:
        raise RuntimeError(
            f"Could not rename the live repository to its backup. No repository contents were deleted or replaced. "
            f"Change to a directory outside {repo_local_root} in the shell that launched StackOps, "
            f"close other tools using the repository, then retry. "
            f"Downloaded copy: {repo_remote_root}. Staged replacement: {staged_root}. {error}"
        ) from error

    installed = False
    try:
        if os.path.lexists(repo_local_root):
            raise FileExistsError(f"Another path appeared at the repository destination: {repo_local_root}")
        staged_root.rename(repo_local_root)
        installed = True
        if _replacement_repository_head(repo_root=repo_local_root) != expected_head:
            raise RuntimeError("The installed repository does not match the validated replacement commit.")
    except BaseException as error:
        try:
            if installed:
                repo_local_root.rename(staged_root)
            if os.path.lexists(repo_local_root):
                raise FileExistsError(f"Refusing to overwrite an existing path during rollback: {repo_local_root}")
            backup_root.rename(repo_local_root)
        except OSError as rollback_error:
            raise RuntimeError(
                f"Repository replacement failed and automatic rollback could not complete. "
                f"Original repository backup: {backup_root}. Downloaded copy: {repo_remote_root}. "
                f"Replacement may be at {repo_local_root} or {staged_root}. "
                f"Replacement error: {error}. Rollback error: {rollback_error}"
            ) from rollback_error
        if not isinstance(error, Exception):
            raise
        raise RuntimeError(
            f"Repository replacement failed; the original repository was restored to {repo_local_root}. "
            f"Downloaded copy: {repo_remote_root}. Staged replacement: {staged_root}. {error}"
        ) from error

    console.print(
        f"Repository replacement verified. Original repository backup retained: {backup_root}\n"
        f"Downloaded copy retained: {repo_remote_root}",
        markup=False,
    )
