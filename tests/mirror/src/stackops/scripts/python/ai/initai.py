import importlib
from pathlib import Path

import pytest

import stackops.scripts.python.ai.scripts.paths as ai_script_paths
initai_module = importlib.import_module("stackops.scripts.python.ai.initai")


def test_snapshot_repo_files_skips_git_directory(tmp_path: Path) -> None:
    normal_file = tmp_path / "notes.txt"
    normal_file.write_text("hello", encoding="utf-8")
    git_file = tmp_path / ".git" / "config"
    git_file.parent.mkdir(parents=True)
    git_file.write_text("ignored", encoding="utf-8")

    snapshot = initai_module._snapshot_repo_files(repo_root=tmp_path)

    assert Path("notes.txt") in snapshot
    assert Path(".git/config") not in snapshot


def test_collect_touched_files_sorts_results_and_skips_gitignore() -> None:
    before = {Path("a.txt"): (1, 10), Path(".gitignore"): (1, 5)}
    after = {Path("b.txt"): (2, 20), Path("a.txt"): (1, 11), Path(".gitignore"): (2, 6)}

    touched_files = initai_module._collect_touched_files(before=before, after=after)

    assert touched_files == ["a.txt", "b.txt"]


def test_add_ai_configs_creates_scaffold_and_tracks_touched_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    framework_calls: list[str] = []
    vscode_calls: list[Path] = []
    scaffold_calls: list[Path] = []
    gitignore_calls: list[tuple[Path, bool, tuple[str, ...]]] = []
    snapshots = iter([{Path("unchanged.txt"): (1, 10)}, {Path("unchanged.txt"): (1, 10), Path("new.txt"): (2, 20)}])

    def fake_get_repo_root(repo_root: Path) -> None:
        return None

    def fake_snapshot_repo_files(repo_root: Path) -> dict[Path, tuple[int, int]]:
        return next(snapshots)

    def fake_collect_touched_files(before: dict[Path, tuple[int, int]], after: dict[Path, tuple[int, int]]) -> list[str]:
        assert before == {Path("unchanged.txt"): (1, 10)}
        assert after == {Path("unchanged.txt"): (1, 10), Path("new.txt"): (2, 20)}
        return ["new.txt"]

    def fake_create_dot_scripts(repo_root: Path) -> None:
        scaffold_calls.append(repo_root)

    def fake_add_lint_and_type_check_task(repo_root: Path) -> None:
        vscode_calls.append(repo_root)

    def fake_build_framework_config(repo_root: Path, framework: str, add_private_config: bool, add_instructions: bool) -> None:
        framework_calls.append(framework)
        assert repo_root == tmp_path
        assert add_private_config is False
        assert add_instructions is True

    def fake_adjust_gitignore(repo_root: Path, include_default_entries: bool, extra_entries: list[str]) -> None:
        gitignore_calls.append((repo_root, include_default_entries, tuple(extra_entries)))

    monkeypatch.setattr(initai_module, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(initai_module, "_snapshot_repo_files", fake_snapshot_repo_files)
    monkeypatch.setattr(initai_module, "_collect_touched_files", fake_collect_touched_files)
    monkeypatch.setattr(initai_module.generic, "create_dot_scripts", fake_create_dot_scripts)
    monkeypatch.setattr(initai_module, "add_lint_and_type_check_task", fake_add_lint_and_type_check_task)
    monkeypatch.setattr(initai_module, "_build_framework_config", fake_build_framework_config)
    monkeypatch.setattr(initai_module.generic, "adjust_gitignore", fake_adjust_gitignore)

    initai_module.add_ai_configs(
        repo_root=tmp_path,
        frameworks=("copilot", "copilot", "codex"),
        include_common_scaffold=True,
        add_all_touched_configs_to_gitignore=True,
        add_vscode_task=True,
        add_private_config=False,
        add_instructions=True,
    )

    assert framework_calls == ["copilot", "codex"]
    assert scaffold_calls == [tmp_path]
    assert vscode_calls == [tmp_path]
    assert gitignore_calls == [(tmp_path, False, ("new.txt",))]
    assert (tmp_path / ".ai").is_dir()
    assert tmp_path.joinpath(ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY.parent).is_dir()
    assert (tmp_path / ".gitignore").exists()
