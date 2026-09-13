import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops.stackops_release import StackOpsRelease, read_stackops_project
from stackops.scripts.python.helpers.helpers_devops.stackops_release_constants import (
    STACKOPS_RELEASE_BRANCH,
    STACKOPS_RELEASE_REPOSITORY,
)
from stackops.scripts.python.helpers.helpers_devops.stackops_versioning import get_next_stackops_version


@dataclass(frozen=True)
class StackOpsPublication:
    repository: str
    parent_commit: str


def _git_output(repo_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(["git", *arguments], cwd=repo_root, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"""git {' '.join(arguments)} failed:\n{error.stderr.strip()}""") from error
    return result.stdout.rstrip("\n")


def _publication_repository(repo_root: Path) -> str:
    urls = [
        _git_output(repo_root, ["remote", "get-url", "--all", "origin"]),
        _git_output(repo_root, ["remote", "get-url", "--push", "--all", "origin"]),
    ]
    for url in urls:
        match = re.fullmatch(r"(?:https://|ssh://git@|git@)github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?", url)
        if match is None or f"""github.com/{match.group(1)}""".lower() != STACKOPS_RELEASE_REPOSITORY:
            raise RuntimeError(f"""Publishing requires origin fetch and push URLs for {STACKOPS_RELEASE_REPOSITORY}.""")
    return STACKOPS_RELEASE_REPOSITORY


def prepare_stackops_publication(repo_root: Path, today: date) -> StackOpsPublication:
    branch = _git_output(repo_root, ["branch", "--show-current"])
    if branch != STACKOPS_RELEASE_BRANCH:
        raise RuntimeError(f"""Publishing requires the {STACKOPS_RELEASE_BRANCH} branch.""")
    if _git_output(repo_root, ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Publishing requires a clean working tree, including the index and untracked files.")
    repository = _publication_repository(repo_root)
    _git_output(repo_root, ["fetch", "--no-tags", "origin", f"""refs/heads/{STACKOPS_RELEASE_BRANCH}:refs/remotes/origin/{STACKOPS_RELEASE_BRANCH}"""])
    parent_commit = _git_output(repo_root, ["rev-parse", "HEAD"])
    remote_commit = _git_output(repo_root, ["rev-parse", f"""refs/remotes/origin/{STACKOPS_RELEASE_BRANCH}"""])
    if parent_commit != remote_commit:
        raise RuntimeError("Publishing requires HEAD to match origin/main. Sync the branch before creating a release.")
    current_version = read_stackops_project(repo_root=repo_root).get("version")
    if not isinstance(current_version, str):
        raise ValueError("StackOps pyproject.toml must contain a string project.version.")
    tag = f"""v{get_next_stackops_version(current_version=current_version, today=today)}"""
    if _git_output(repo_root, ["tag", "--list", tag]) or _git_output(repo_root, ["ls-remote", "--tags", "origin", f"""refs/tags/{tag}"""]):
        raise RuntimeError(f"""Release tag {tag} already exists. Inspect the existing release before publishing.""")
    return StackOpsPublication(repository=repository, parent_commit=parent_commit)


def publish_stackops_release(repo_root: Path, release: StackOpsRelease, publication: StackOpsPublication) -> str:
    branch = _git_output(repo_root, ["branch", "--show-current"])
    parent_commit = _git_output(repo_root, ["rev-parse", "HEAD"])
    if branch != STACKOPS_RELEASE_BRANCH or parent_commit != publication.parent_commit:
        raise RuntimeError("The branch or HEAD changed after release preflight. Release files remain local; inspect them before publishing.")
    if _publication_repository(repo_root) != publication.repository:
        raise RuntimeError("The origin repository changed after release preflight.")
    changed_paths = _git_output(repo_root, ["diff", "--name-only", "-z", "HEAD"]).split("\0")
    untracked_paths = _git_output(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"]).split("\0")
    actual_files = {Path(path) for path in [*changed_paths, *untracked_paths] if path}
    if not release.changed_files or actual_files != set(release.changed_files):
        raise RuntimeError("Working tree changes differ from the release files. Inspect the local changes before publishing.")
    release_paths = [path.as_posix() for path in release.changed_files]
    tag = f"""v{release.version}"""
    if _git_output(repo_root, ["tag", "--list", tag]) or _git_output(repo_root, ["ls-remote", "--tags", "origin", f"""refs/tags/{tag}"""]):
        raise RuntimeError(f"""Release tag {tag} already exists. Inspect the existing release before publishing.""")
    _git_output(repo_root, ["add", "--", *release_paths])
    try:
        _git_output(repo_root, ["commit", "--only", "--message", f"""chore(release): bump to v{release.version}""", "--", *release_paths])
    except RuntimeError as error:
        raise RuntimeError(f"""{error}\nRelease {release.version} remains local. Fix the commit failure and commit these files without bumping again.""") from error
    commit = _git_output(repo_root, ["rev-parse", "HEAD"])
    if _git_output(repo_root, ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError(f"""Release commit {commit} exists locally, but the working tree changed while committing. Inspect it before pushing.""")
    try:
        _git_output(repo_root, ["tag", "--annotate", tag, "--message", f"""Release {tag}""", commit])
        _git_output(repo_root, ["push", "--atomic", "origin", f"""{commit}:refs/heads/{STACKOPS_RELEASE_BRANCH}""", f"""refs/tags/{tag}:refs/tags/{tag}"""])
    except RuntimeError as error:
        raise RuntimeError(
            f"""{error}\nRelease commit {commit} exists locally. Resolve the failure and push this commit and {tag} together; do not bump the version again."""
        ) from error
    return tag
