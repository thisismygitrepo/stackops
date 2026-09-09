from pathlib import Path

import git
import typer

from stackops.utils.source_of_truth import STACKOPS_REPO_DIR

AUTO_COMMIT_MESSAGE = "chore: auto-commit local changes before stackops update"


def developer_repo_root() -> Path | None:
    if STACKOPS_REPO_DIR.joinpath("pyproject.toml").is_file():
        return STACKOPS_REPO_DIR
    return None


def _abort_rebase_if_in_progress(repo: git.Repo) -> None:
    git_dir = Path(repo.git_dir)
    if git_dir.joinpath("rebase-merge").exists() or git_dir.joinpath("rebase-apply").exists():
        repo.git.rebase(abort=True)


def sync_dev_repo_before_update(dev_repo_root: Path) -> None:
    repo = git.Repo(str(dev_repo_root))
    if repo.head.is_detached:
        typer.echo(f"❌ --dev sync requires a checked-out branch, HEAD in {str(dev_repo_root)} is detached.")
        raise typer.Exit(code=1)
    try:
        if repo.is_dirty(untracked_files=True):
            repo.git.add("-A")
            repo.git.commit(message=AUTO_COMMIT_MESSAGE)
            typer.echo(f"🧹 Committed local changes: {AUTO_COMMIT_MESSAGE}")
        repo.git.pull(rebase=True, autostash=True)
        repo.remotes.origin.push()
    except git.GitCommandError as error:
        _abort_rebase_if_in_progress(repo)
        typer.echo(
            f"❌ Syncing {str(dev_repo_root)} with origin failed, update aborted before touching uv/stackops.\n"
            f"   Fix the repo state manually (e.g. resolve conflicts, check remote access), then rerun the update.\n{error}"
        )
        raise typer.Exit(code=1) from None
    typer.echo("✅ Repo synced with origin (pull --rebase + push).")
