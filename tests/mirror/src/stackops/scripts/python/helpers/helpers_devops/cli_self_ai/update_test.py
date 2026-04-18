from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_test as update_test_module


def test_should_include_python_context_path_excludes_tests_and_non_python_files() -> None:
    should_include_path = cast(Callable[..., bool], getattr(update_test_module, "_should_include_python_context_path"))

    assert should_include_path(relative_path=Path("src/stackops/app.py"))
    assert not should_include_path(relative_path=Path("tests/test_app.py"))
    assert not should_include_path(relative_path=Path("src/stackops/app.md"))


def test_build_repo_python_context_joins_visible_python_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        update_test_module,
        "_list_git_visible_files",
        lambda *, repo_root: (
            Path("src/stackops/b.py"),
            Path("tests/test_skip.py"),
            Path("src/stackops/a.py"),
            Path("docs/index.md"),
        ),
    )
    build_repo_python_context = cast(Callable[..., str], getattr(update_test_module, "_build_repo_python_context"))

    result = build_repo_python_context(repo_root=tmp_path)

    assert result == update_test_module.DEFAULT_SEAPRATOR.join(("src/stackops/b.py", "src/stackops/a.py"))


def test_update_test_writes_context_file_even_when_agent_creation_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(update_test_module, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_test_module, "_build_repo_python_context", lambda *, repo_root: "src/stackops/a.py@-@src/stackops/b.py")
    monkeypatch.setattr(update_test_module, "agents_create_impl", fake_agents_create_impl)

    with pytest.raises(RuntimeError, match="boom"):
        update_test_module.update_test()

    context_path = repo_root.joinpath(".ai", "agents", update_test_module.DEFAULT_TEST_JOB_NAME, "context.md")

    assert captured["context"] == "src/stackops/a.py@-@src/stackops/b.py"
    assert captured["prompt"] == update_test_module.UPDATE_TEST_PROMPT
    assert context_path.read_text(encoding="utf-8") == "src/stackops/a.py@-@src/stackops/b.py"
