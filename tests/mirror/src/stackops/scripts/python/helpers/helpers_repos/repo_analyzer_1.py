

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from stackops.scripts.python.helpers.helpers_repos import repo_analyzer_1 as analyzer_module


fetch_calls: list[tuple[str, ...]] = []


@dataclass
class FakeBlob:
    path: str
    payload: bytes | None

    @property
    def data_stream(self) -> SimpleNamespace:
        if self.payload is None:
            raise RuntimeError("unreadable")
        return SimpleNamespace(read=lambda: self.payload)


class FakeTree:
    def __init__(self, blobs: list[FakeBlob]) -> None:
        self._blobs = blobs

    def traverse(self) -> list[FakeBlob]:
        return self._blobs


class FakeRefs:
    def __init__(self, names: set[str]) -> None:
        self._names = names

    def __getitem__(self, key: str) -> object:
        if key not in self._names:
            raise IndexError(key)
        return object()


class FakeCommitStats:
    def __init__(self, files: dict[str, dict[str, int]]) -> None:
        self.files = files


class FakeHistoryCommit:
    def __init__(self, hexsha: str, committed_at: datetime, parents: list[object], files: dict[str, dict[str, int]]) -> None:
        self.hexsha = hexsha
        self.committed_date = int(committed_at.timestamp())
        self.parents = parents
        self.stats = FakeCommitStats(files)


class FakeRepoForHistory:
    def __init__(self, commits: list[FakeHistoryCommit], git_dir: Path) -> None:
        self._commits = commits
        self.git_dir = str(git_dir)
        self.git = SimpleNamespace(fetch=lambda *args: fetch_calls.append(args))
        self.head = SimpleNamespace(reference=SimpleNamespace(name="develop"))
        self.refs = FakeRefs({"main"})

    def iter_commits(self, _branch_name: str | None = None):
        return iter(self._commits)


def test_count_python_lines_counts_only_python_files() -> None:
    commit = SimpleNamespace(
        hexsha="deadbeef",
        tree=FakeTree(
            [
                FakeBlob("pkg/a.py", b"print(1)\nprint(2)\n"),
                FakeBlob("pkg/b.txt", b"skip\n"),
                FakeBlob("pkg/c.py", None),
            ]
        ),
    )

    assert analyzer_module.count_python_lines(commit) == (2, 1)


def test_get_default_branch_prefers_main_then_master_then_head() -> None:
    repo_main = SimpleNamespace(refs=FakeRefs({"main"}), head=SimpleNamespace(reference=SimpleNamespace(name="topic")))
    repo_master = SimpleNamespace(refs=FakeRefs({"master"}), head=SimpleNamespace(reference=SimpleNamespace(name="topic")))
    repo_head = SimpleNamespace(refs=FakeRefs(set()), head=SimpleNamespace(reference=SimpleNamespace(name="topic")))

    assert analyzer_module.get_default_branch(cast(object, repo_main)) == "main"
    assert analyzer_module.get_default_branch(cast(object, repo_master)) == "master"
    assert analyzer_module.get_default_branch(cast(object, repo_head)) == "topic"


def test_count_historical_line_edits_sums_python_insertions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commits = [
        FakeHistoryCommit("a1", datetime(2023, 1, 1, tzinfo=timezone.utc), [], {"a.py": {"insertions": 3}, "notes.txt": {"insertions": 8}}),
        FakeHistoryCommit("b2", datetime(2023, 1, 2, tzinfo=timezone.utc), [object()], {"pkg/b.py": {"insertions": 5}}),
    ]
    repo = FakeRepoForHistory(commits=commits, git_dir=tmp_path / ".git")

    monkeypatch.setattr(analyzer_module, "Repo", lambda repo_path: repo)
    monkeypatch.setattr(analyzer_module, "count_python_lines", lambda commit: (10, 2))
    called: list[tuple[str, bool]] = []
    monkeypatch.setattr(analyzer_module, "gitcs_viz", lambda repo_path, pull_full_history: called.append((str(repo_path), pull_full_history)))

    total = analyzer_module.count_historical_line_edits(repo_path=str(tmp_path))

    assert total == 8
    assert called == [(str(tmp_path), True)]


def test_gitcs_viz_fetches_full_history_and_runs_half_year_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    git_dir.joinpath("shallow").write_text("", encoding="utf-8")
    commits = [
        FakeHistoryCommit("a1", datetime(2022, 3, 1, tzinfo=timezone.utc), [], {}),
        FakeHistoryCommit("b2", datetime(2023, 8, 1, tzinfo=timezone.utc), [object()], {}),
    ]
    repo = FakeRepoForHistory(commits=commits, git_dir=git_dir)
    commands: list[list[str]] = []

    import stackops.utils.installer_utils.installer_cli as installer_cli

    monkeypatch.setattr(installer_cli, "install_if_missing", lambda which, binary_name, verbose: None)
    monkeypatch.setattr(analyzer_module, "Repo", lambda repo_path: repo)
    monkeypatch.setattr(
        analyzer_module.subprocess,
        "run",
        lambda cmd, cwd, capture_output, text: commands.append(cmd) or SimpleNamespace(stdout="", stderr="", returncode=0),
    )
    fetch_calls.clear()

    analyzer_module.gitcs_viz(repo_path=tmp_path, email="dev@example.com", pull_full_history=True)

    assert fetch_calls == [("--unshallow",)]
    assert len(commands) == 4
    assert commands[0] == ["gitcs", "-path", str(tmp_path.resolve()), "-since", "2022-01-01", "-until", "2022-06-30", "-email", "dev@example.com"]
    assert commands[-1][4:8] == ["2023-07-01", "-until", "2023-12-31", "-email"]
