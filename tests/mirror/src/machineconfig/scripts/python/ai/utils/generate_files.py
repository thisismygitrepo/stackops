from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import machineconfig.scripts.python.ai.utils.generate_files as generate_files_module


def _init_git_repository(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)


def test_make_todo_files_generates_filtered_markdown_and_cleans_old_todo_dir(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    _init_git_repository(repo_root)

    stale_file = repo_root.joinpath(".ai", "todo", "stale.md")
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("stale", encoding="utf-8")

    package_dir = repo_root.joinpath("pkg")
    package_dir.mkdir()
    package_dir.joinpath("__init__.py").write_text("", encoding="utf-8")
    package_dir.joinpath("app.py").write_text("print('ok')\n", encoding="utf-8")

    tools_dir = repo_root.joinpath("tools")
    tools_dir.mkdir()
    tools_dir.joinpath("build.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    repo_root.joinpath(".ai", "internal.py").write_text("print('skip')\n", encoding="utf-8")

    generate_files_module.make_todo_files(
        pattern="pkg",
        repo=str(repo_root),
        strategy="name",
        exclude_init=True,
        include_line_count=True,
        output_path=".ai/todo/files",
        format_type="md",
        split_every=None,
        split_to=None,
    )

    output_file = repo_root.joinpath(".ai", "todo", "files.md")

    assert output_file.exists()
    assert not stale_file.exists()

    output = output_file.read_text(encoding="utf-8")

    assert "Line Count" in output
    assert "pkg/app.py" in output
    assert "pkg/__init__.py" not in output
    assert ".ai/internal.py" not in output
    assert "tools/build.sh" not in output


def test_make_todo_files_resolves_git_root_from_nested_directory(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    _init_git_repository(repo_root)

    nested_dir = repo_root.joinpath("apps", "service")
    nested_dir.mkdir(parents=True)
    nested_dir.joinpath("main.py").write_text("print('ok')\n", encoding="utf-8")

    generate_files_module.make_todo_files(
        pattern=".py",
        repo=str(nested_dir),
        strategy="name",
        exclude_init=True,
        include_line_count=False,
        output_path=".ai/todo/files",
        format_type="md",
        split_every=None,
        split_to=None,
    )

    output_file = repo_root.joinpath(".ai", "todo", "files.md")

    assert output_file.exists()
    output = output_file.read_text(encoding="utf-8")
    assert "apps/service/main.py" in output


def test_make_todo_files_accepts_workspace_with_multiple_git_repositories(tmp_path: Path) -> None:
    workspace_root = tmp_path.joinpath("workspace")
    workspace_root.mkdir()

    repo_one = workspace_root.joinpath("repo_one")
    repo_one.mkdir()
    _init_git_repository(repo_one)
    repo_one.joinpath("app.py").write_text("print('one')\n", encoding="utf-8")

    repo_two = workspace_root.joinpath("repo_two")
    repo_two.mkdir()
    _init_git_repository(repo_two)
    repo_two.joinpath("tool.py").write_text("print('two')\n", encoding="utf-8")

    generate_files_module.make_todo_files(
        pattern=".py",
        repo=str(workspace_root),
        strategy="name",
        exclude_init=True,
        include_line_count=False,
        output_path=".ai/todo/files",
        format_type="md",
        split_every=None,
        split_to=None,
    )

    output_file = workspace_root.joinpath(".ai", "todo", "files.md")

    assert output_file.exists()
    output = output_file.read_text(encoding="utf-8")
    assert "repo_one/app.py" in output
    assert "repo_two/tool.py" in output


def test_create_repo_symlinks_creates_five_links_in_code_copies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()

    home_dir = tmp_path.joinpath("home")
    copies_dir = home_dir.joinpath("code_copies")
    copies_dir.mkdir(parents=True)
    copies_dir.joinpath("repo_copy_1").write_text("stale", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: home_dir)

    generate_files_module.create_repo_symlinks(repo_root=repo_root)

    for index in range(1, 6):
        symlink_path = copies_dir.joinpath(f"repo_copy_{index}")
        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == repo_root.resolve()
