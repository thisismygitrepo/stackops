import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_devops import stackops_publish
from stackops.scripts.python.helpers.helpers_devops.stackops_release import StackOpsRelease


@dataclass(frozen=True)
class ReleaseRepository:
    root: Path
    remote: Path
    commands: list[list[str]]


def _git(repo_root: Path, arguments: list[str]) -> str:
    result = subprocess.run(["git", *arguments], cwd=repo_root, capture_output=True, text=True, check=True)
    return result.stdout.strip()


@pytest.fixture
def release_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReleaseRepository:
    repo_root = tmp_path / "checkout"
    remote = tmp_path / "origin.git"
    repo_root.mkdir()
    _git(tmp_path, ["init", "--bare", "--initial-branch=main", str(remote)])
    _git(repo_root, ["init", "--initial-branch=main"])
    _git(repo_root, ["config", "user.name", "Release Test"])
    _git(repo_root, ["config", "user.email", "release@example.invalid"])
    _git(repo_root, ["config", "commit.gpgsign", "false"])
    _git(repo_root, ["config", "tag.gpgsign", "false"])
    (repo_root / "release.txt").write_text("26.9.2\n", encoding="utf-8")
    _git(repo_root, ["add", "release.txt"])
    _git(repo_root, ["commit", "--message", "Initial release"])
    _git(repo_root, ["push", str(remote), "HEAD:refs/heads/main"])
    _git(repo_root, ["remote", "add", "origin", "https://github.com/thisismygitrepo/stackops.git"])
    original_run = subprocess.run
    commands: list[list[str]] = []

    def fake_network(command: list[str], cwd: Path, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert command[0] == "git"
        commands.append(command.copy())
        if command[1] in {"fetch", "push", "ls-remote"} and "origin" in command:
            command = [str(remote) if argument == "origin" else argument for argument in command]
        return original_run(command, cwd=cwd, capture_output=capture_output, text=text, check=check)

    def project_version(repo_root: Path) -> dict[str, object]:
        return {"name": "stackops", "version": repo_root.joinpath("release.txt").read_text(encoding="utf-8").strip()}

    monkeypatch.setattr(subprocess, "run", fake_network)
    monkeypatch.setattr(stackops_publish, "read_stackops_project", project_version)
    return ReleaseRepository(root=repo_root, remote=remote, commands=commands)


def test_publish_pushes_release_commit_and_annotated_tag_atomically(release_repository: ReleaseRepository) -> None:
    repo_root = release_repository.root
    publication = stackops_publish.prepare_stackops_publication(repo_root=repo_root, today=date(2026, 9, 13))
    (repo_root / "release.txt").write_text("26.9.3\n", encoding="utf-8")
    release = StackOpsRelease(previous_version="26.9.2", version="26.9.3", changed_files=(Path("release.txt"),))

    tag = stackops_publish.publish_stackops_release(repo_root=repo_root, release=release, publication=publication)

    commit = _git(repo_root, ["rev-parse", "HEAD"])
    assert tag == "v26.9.3"
    assert _git(repo_root, ["rev-parse", f"""{tag}^{{}}"""]) == commit
    assert _git(repo_root, ["cat-file", "-t", tag]) == "tag"
    assert _git(release_repository.remote, ["rev-parse", "refs/heads/main"]) == commit
    assert _git(release_repository.remote, ["rev-parse", f"""refs/tags/{tag}^{{}}"""]) == commit
    assert _git(repo_root, ["show", "--format=", "--name-only", "HEAD"]) == "release.txt"
    assert _git(repo_root, ["status", "--porcelain"]) == ""
    assert ["git", "push", "--atomic", "origin", f"""{commit}:refs/heads/main""", f"""refs/tags/{tag}:refs/tags/{tag}"""] in release_repository.commands


@pytest.mark.parametrize("state", ["dirty", "staged", "untracked", "branch", "detached", "ahead", "behind", "diverged"])
def test_preflight_rejects_unsuitable_git_state(release_repository: ReleaseRepository, state: str) -> None:
    repo_root = release_repository.root
    if state in {"dirty", "staged"}:
        (repo_root / "release.txt").write_text("local edit\n", encoding="utf-8")
        if state == "staged":
            _git(repo_root, ["add", "release.txt"])
    elif state == "untracked":
        (repo_root / "untracked.txt").write_text("local file\n", encoding="utf-8")
    elif state == "branch":
        _git(repo_root, ["switch", "--create", "feature"])
    elif state == "detached":
        _git(repo_root, ["checkout", "--detach"])
    else:
        original_commit = _git(repo_root, ["rev-parse", "HEAD"])
        _git(repo_root, ["commit", "--allow-empty", "--message", "Advance main"])
        if state in {"behind", "diverged"}:
            _git(repo_root, ["push", str(release_repository.remote), "HEAD:refs/heads/main"])
            _git(repo_root, ["reset", "--hard", original_commit])
            if state == "diverged":
                _git(repo_root, ["commit", "--allow-empty", "--message", "Diverge main"])

    with pytest.raises(RuntimeError, match="requires"):
        stackops_publish.prepare_stackops_publication(repo_root=repo_root, today=date(2026, 9, 13))


@pytest.mark.parametrize("remote_tag", [False, True])
def test_preflight_rejects_existing_local_or_remote_tag(release_repository: ReleaseRepository, remote_tag: bool) -> None:
    repo_root = release_repository.root
    _git(repo_root, ["tag", "v26.9.3"])
    if remote_tag:
        _git(repo_root, ["push", str(release_repository.remote), "refs/tags/v26.9.3"])
        _git(repo_root, ["tag", "--delete", "v26.9.3"])

    with pytest.raises(RuntimeError, match="tag v26.9.3 already exists"):
        stackops_publish.prepare_stackops_publication(repo_root=repo_root, today=date(2026, 9, 13))
    assert (repo_root / "release.txt").read_text(encoding="utf-8") == "26.9.2\n"


@pytest.mark.parametrize("remote_change", ["missing", "fetch", "push", "multiple"])
def test_preflight_rejects_mismatched_origin(release_repository: ReleaseRepository, remote_change: str) -> None:
    repo_root = release_repository.root
    wrong_remote = "git@github.com:someone/stackops.git"
    match remote_change:
        case "missing":
            _git(repo_root, ["remote", "remove", "origin"])
        case "fetch":
            _git(repo_root, ["remote", "set-url", "origin", wrong_remote])
        case "push":
            _git(repo_root, ["remote", "set-url", "--push", "origin", wrong_remote])
        case "multiple":
            _git(repo_root, ["remote", "set-url", "--add", "origin", wrong_remote])
    with pytest.raises(RuntimeError):
        stackops_publish.prepare_stackops_publication(repo_root=repo_root, today=date(2026, 9, 13))


def test_publish_rejects_changes_added_after_preflight(release_repository: ReleaseRepository) -> None:
    repo_root = release_repository.root
    publication = stackops_publish.prepare_stackops_publication(repo_root=repo_root, today=date(2026, 9, 13))
    (repo_root / "release.txt").write_text("26.9.3\n", encoding="utf-8")
    (repo_root / "unrelated.txt").write_text("Concurrent work\n", encoding="utf-8")
    release = StackOpsRelease(previous_version="26.9.2", version="26.9.3", changed_files=(Path("release.txt"),))

    with pytest.raises(RuntimeError, match="differ from the release files"):
        stackops_publish.publish_stackops_release(repo_root=repo_root, release=release, publication=publication)
    assert _git(repo_root, ["rev-parse", "HEAD"]) == publication.parent_commit


def test_rejected_atomic_push_keeps_both_remote_refs_unchanged(release_repository: ReleaseRepository) -> None:
    repo_root = release_repository.root
    publication = stackops_publish.prepare_stackops_publication(repo_root=repo_root, today=date(2026, 9, 13))
    (repo_root / "release.txt").write_text("26.9.3\n", encoding="utf-8")
    release = StackOpsRelease(previous_version="26.9.2", version="26.9.3", changed_files=(Path("release.txt"),))
    hook = release_repository.remote / "hooks" / "update"
    hook.write_text('''#!/bin/sh
if [ "$1" = "refs/tags/v26.9.3" ]; then
    exit 1
fi
''', encoding="utf-8")
    hook.chmod(0o755)

    with pytest.raises(RuntimeError, match="do not bump the version again"):
        stackops_publish.publish_stackops_release(repo_root=repo_root, release=release, publication=publication)

    commit = _git(repo_root, ["rev-parse", "HEAD"])
    assert commit != publication.parent_commit
    assert _git(repo_root, ["rev-parse", "v26.9.3^{}"]) == commit
    assert _git(release_repository.remote, ["rev-parse", "refs/heads/main"]) == publication.parent_commit
    assert _git(release_repository.remote, ["tag", "--list", "v26.9.3"]) == ""
