import hashlib
import os
import subprocess
from pathlib import Path
from typing import Literal, TypedDict

import git


RepositoryUpdateStatus = Literal["success", "error", "skipped", "auth_failed"]


class RepositoryUpdateResult(TypedDict):
    """Result of updating a single repository."""

    repo_path: str
    status: RepositoryUpdateStatus
    had_uncommitted_changes: bool
    uncommitted_files: list[str]
    commit_before: str
    commit_after: str
    commits_changed: bool
    pyproject_changed: bool
    dependencies_changed: bool
    uv_sync_ran: bool
    uv_sync_success: bool
    remotes_processed: list[str]
    remotes_skipped: list[str]
    error_message: str | None
    is_stackops_repo: bool
    permissions_updated: bool


def set_permissions_recursive(path: Path, executable: bool) -> None:
    """Set permissions recursively for a directory."""
    if not path.exists():
        return
    if path.is_file():
        if executable:
            path.chmod(0o755)
        else:
            path.chmod(0o644)
    elif path.is_dir():
        path.chmod(0o755)
        for item in path.rglob("*"):
            set_permissions_recursive(path=item, executable=executable)


def run_uv_sync(repo_path: Path) -> bool:
    """Run uv sync in the given repository path. Returns True if successful."""
    try:
        subprocess.run(["uv", "sync", "--no-dev"], cwd=repo_path, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def get_file_hash(file_path: Path) -> str | None:
    """Get SHA256 hash of a file, return None if file doesn't exist."""
    if not file_path.exists():
        return None
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def update_repository(repo: git.Repo, auto_uv_sync: bool, allow_password_prompt: bool) -> RepositoryUpdateResult:
    """Update a single repository and return detailed information about what happened."""
    repo_path = Path(repo.working_dir)

    # Initialize result dict
    result: RepositoryUpdateResult = {
        "repo_path": str(repo_path),
        "status": "success",
        "had_uncommitted_changes": False,
        "uncommitted_files": [],
        "commit_before": "",
        "commit_after": "",
        "commits_changed": False,
        "pyproject_changed": False,
        "dependencies_changed": False,
        "uv_sync_ran": False,
        "uv_sync_success": False,
        "remotes_processed": [],
        "remotes_skipped": [],
        "error_message": None,
        "is_stackops_repo": "stackops" in str(repo_path),
        "permissions_updated": False,
    }

    if repo.is_dirty():
        # Get the list of modified files
        changed_files_raw = [item.a_path for item in repo.index.diff(None)]
        changed_files_raw.extend([item.a_path for item in repo.index.diff("HEAD")])
        # Filter out None values and remove duplicates
        changed_files = list(set(file for file in changed_files_raw if file is not None))

        result["had_uncommitted_changes"] = True
        result["uncommitted_files"] = changed_files
        result["status"] = "error"
        result["error_message"] = (
            f"Cannot update repository - there are pending changes in: {', '.join(changed_files)}. Please commit or stash your changes first."
        )
        raise RuntimeError(result["error_message"])

    # Check if this repo has pyproject.toml
    pyproject_path = repo_path / "pyproject.toml"

    # Get hashes before pull
    pyproject_hash_before = get_file_hash(pyproject_path)

    # Get current commit hash before pull
    result["commit_before"] = repo.head.commit.hexsha

    try:
        remotes = list(repo.remotes)
        if not remotes:
            result["status"] = "skipped"
            result["error_message"] = "No remotes configured for this repository"
            return result

        remote_errors: list[str] = []
        for remote in remotes:
            try:
                env = None
                if not allow_password_prompt:
                    env = os.environ.copy()
                    env["GIT_TERMINAL_PROMPT"] = "0"
                    env["GIT_ASKPASS"] = "echo"

                fetch_result = subprocess.run(
                    ["git", "fetch", remote.name, "--verbose"], cwd=repo_path, capture_output=True, text=True, env=env, timeout=30
                )

                if fetch_result.returncode != 0 and not allow_password_prompt:
                    auth_error_indicators = [
                        "Authentication failed",
                        "Password for",
                        "Username for",
                        "could not read Username",
                        "could not read Password",
                        "fatal: Authentication failed",
                        "fatal: could not read Username",
                        "fatal: could not read Password",
                    ]

                    error_output = (fetch_result.stderr or "") + (fetch_result.stdout or "")
                    if any(indicator in error_output for indicator in auth_error_indicators):
                        result["remotes_skipped"].append(remote.name)
                        remote_errors.append(f"{remote.name}: authentication required")
                        continue

                if fetch_result.returncode != 0:
                    result["remotes_skipped"].append(remote.name)
                    fetch_error = (fetch_result.stderr or fetch_result.stdout).strip()
                    remote_errors.append(f"{remote.name}: {fetch_error or f'fetch exited {fetch_result.returncode}'}")
                    continue

                pull_result = subprocess.run(
                    ["git", "pull", remote.name, repo.active_branch.name, "--verbose"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30,
                )

                if pull_result.returncode != 0 and not allow_password_prompt:
                    auth_error_indicators = [
                        "Authentication failed",
                        "Password for",
                        "Username for",
                        "could not read Username",
                        "could not read Password",
                        "fatal: Authentication failed",
                        "fatal: could not read Username",
                        "fatal: could not read Password",
                    ]

                    error_output = (pull_result.stderr or "") + (pull_result.stdout or "")
                    if any(indicator in error_output for indicator in auth_error_indicators):
                        result["remotes_skipped"].append(remote.name)
                        remote_errors.append(f"{remote.name}: authentication required")
                        continue

                if pull_result.returncode == 0:
                    result["remotes_processed"].append(remote.name)
                    result["commit_after"] = repo.head.commit.hexsha
                    if result["commit_before"] != result["commit_after"]:
                        result["commits_changed"] = True
                else:
                    result["remotes_skipped"].append(remote.name)
                    pull_error = (pull_result.stderr or pull_result.stdout).strip()
                    remote_errors.append(f"{remote.name}: {pull_error or f'pull exited {pull_result.returncode}'}")

            except Exception as error:
                result["remotes_skipped"].append(remote.name)
                remote_errors.append(f"{remote.name}: {error}")

        if remote_errors:
            result["status"] = "error"
            result["error_message"] = "; ".join(remote_errors)

        # Check if pyproject.toml changed after pull
        pyproject_hash_after = get_file_hash(pyproject_path)

        if pyproject_hash_before != pyproject_hash_after:
            result["pyproject_changed"] = True
            result["dependencies_changed"] = True

        if result["is_stackops_repo"]:
            scripts_path = Path.home() / "scripts"
            if scripts_path.exists():
                set_permissions_recursive(path=scripts_path, executable=True)
                result["permissions_updated"] = True

            linux_jobs_path = repo_path / "src" / "stackops" / "jobs" / "linux"
            if linux_jobs_path.exists():
                set_permissions_recursive(path=linux_jobs_path, executable=True)
                result["permissions_updated"] = True

        # Run uv sync if dependencies changed and auto_sync is enabled
        if result["dependencies_changed"] and auto_uv_sync:
            result["uv_sync_ran"] = True
            result["uv_sync_success"] = run_uv_sync(repo_path)
            if not result["uv_sync_success"]:
                result["status"] = "error"
                result["error_message"] = "uv sync failed"

        return result

    except Exception as error:
        result["status"] = "error"
        result["error_message"] = str(error)
        return result
