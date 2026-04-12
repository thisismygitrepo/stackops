from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai.update_test as update_test_module


def test_should_include_python_context_path_excludes_tests_and_non_python_files() -> None:
    assert update_test_module._should_include_python_context_path(relative_path=Path("src/machineconfig/app.py"))
    assert not update_test_module._should_include_python_context_path(relative_path=Path("tests/test_app.py"))
    assert not update_test_module._should_include_python_context_path(relative_path=Path("src/machineconfig/app.md"))


def test_build_repo_python_context_joins_visible_python_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        update_test_module,
        "_list_git_visible_files",
        lambda *, repo_root: (Path("src/machineconfig/b.py"), Path("tests/test_skip.py"), Path("src/machineconfig/a.py"), Path("docs/index.md")),
    )

    result = update_test_module._build_repo_python_context(repo_root=tmp_path)

    assert result == update_test_module.DEFAULT_SEAPRATOR.join(("src/machineconfig/b.py", "src/machineconfig/a.py"))


def test_update_test_writes_context_file_even_when_agent_creation_fails(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(update_test_module, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_test_module, "_build_repo_python_context", lambda *, repo_root: "src/machineconfig/a.py@-@src/machineconfig/b.py")
    monkeypatch.setattr(update_test_module, "agents_create_impl", fake_agents_create_impl)

    with pytest.raises(RuntimeError, match="boom"):
        update_test_module.update_test()

    context_path = repo_root.joinpath(".ai", "agents", update_test_module.DEFAULT_TEST_JOB_NAME, "context.md")

    assert captured["context"] == "src/machineconfig/a.py@-@src/machineconfig/b.py"
    assert captured["prompt"] == update_test_module.UPDATE_TEST_PROMPT
    assert context_path.read_text(encoding="utf-8") == "src/machineconfig/a.py@-@src/machineconfig/b.py"
