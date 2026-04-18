from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from stat import S_IMODE
from types import SimpleNamespace

import pytest

from stackops.scripts.python.helpers.helpers_repos import update as update_module


@dataclass
class FakeRemote:
    name: str


class FakeCommit:
    def __init__(self, values: list[str]) -> None:
        self._values = values
        self._index = 0

    @property
    def hexsha(self) -> str:
        value = self._values[min(self._index, len(self._values) - 1)]
        self._index += 1
        return value


class FakeRepo:
    def __init__(self, working_dir: Path, dirty: bool, remotes: list[FakeRemote], commit_values: list[str]) -> None:
        self.working_dir = str(working_dir)
        self._dirty = dirty
        self.remotes = remotes
        self.active_branch = SimpleNamespace(name="main")
        self.head = SimpleNamespace(commit=FakeCommit(commit_values))
        self.index = SimpleNamespace(diff=lambda ref: [])

    def is_dirty(self) -> bool:
        return self._dirty


def test_set_permissions_recursive_updates_files_and_directories(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    file_path = root / "nested" / "demo.sh"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("echo hi\n", encoding="utf-8")

    update_module.set_permissions_recursive(root, executable=True)

    assert S_IMODE(root.stat().st_mode) == 0o755
    assert S_IMODE(file_path.stat().st_mode) == 0o755


def test_get_file_hash_matches_sha256_and_handles_missing_file(tmp_path: Path) -> None:
    file_path = tmp_path / "demo.txt"
    file_path.write_text("abc", encoding="utf-8")

    assert update_module.get_file_hash(file_path) == hashlib.sha256(b"abc").hexdigest()
    assert update_module.get_file_hash(tmp_path / "missing.txt") is None


def test_update_repository_skips_repositories_without_remotes(tmp_path: Path) -> None:
    repo_path = tmp_path / "demo"
    repo_path.mkdir()
    repo = FakeRepo(working_dir=repo_path, dirty=False, remotes=[], commit_values=["a" * 40])

    result = update_module.update_repository(repo=repo, auto_uv_sync=False, allow_password_prompt=False)

    assert result["status"] == "skipped"
    assert result["error_message"] == "No remotes configured for this repository"


def test_update_repository_detects_dependency_changes_and_runs_uv_sync(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_path = tmp_path / "home"
    scripts_path = home_path / "scripts"
    linux_jobs_path = tmp_path / "stackops-demo" / "src" / "stackops" / "jobs" / "linux"
    repo_path = linux_jobs_path.parents[3]
    scripts_path.mkdir(parents=True)
    linux_jobs_path.mkdir(parents=True)
    repo_path.joinpath("pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    repo = FakeRepo(
        working_dir=repo_path,
        dirty=False,
        remotes=[FakeRemote("origin")],
        commit_values=["a" * 40, "b" * 40],
    )

    permissions: list[Path] = []
    hashes = iter(["before", "after"])
    command_log: list[list[str]] = []

    monkeypatch.setattr(update_module.Path, "home", classmethod(lambda cls: home_path))
    monkeypatch.setattr(update_module, "set_permissions_recursive", lambda path, executable=True: permissions.append(path))
    monkeypatch.setattr(update_module, "get_file_hash", lambda file_path: next(hashes))
    monkeypatch.setattr(update_module, "run_uv_sync", lambda path: True)
    monkeypatch.setattr(
        update_module.subprocess,
        "run",
        lambda cmd, cwd, capture_output, text, env=None, timeout=30: command_log.append(cmd) or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    result = update_module.update_repository(repo=repo, auto_uv_sync=True, allow_password_prompt=False)

    assert result["status"] == "success"
    assert result["remotes_processed"] == ["origin"]
    assert result["commits_changed"]
    assert result["pyproject_changed"]
    assert result["dependencies_changed"]
    assert result["uv_sync_ran"]
    assert result["uv_sync_success"]
    assert result["permissions_updated"]
    assert permissions == [scripts_path, linux_jobs_path]
    assert command_log[0][:3] == ["git", "fetch", "origin"]
    assert command_log[1][:3] == ["git", "pull", "origin"]


def test_update_repository_raises_when_uncommitted_changes_exist(tmp_path: Path) -> None:
    repo_path = tmp_path / "demo"
    repo_path.mkdir()
    repo = FakeRepo(working_dir=repo_path, dirty=True, remotes=[FakeRemote("origin")], commit_values=["a" * 40])

    with pytest.raises(RuntimeError, match="Cannot update repository"):
        update_module.update_repository(repo=repo, auto_uv_sync=False, allow_password_prompt=False)
