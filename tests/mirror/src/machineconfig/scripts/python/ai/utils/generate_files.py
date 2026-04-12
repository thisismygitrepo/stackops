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
