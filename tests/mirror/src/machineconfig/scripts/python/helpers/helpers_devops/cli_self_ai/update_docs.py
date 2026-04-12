from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai.update_docs as update_docs_module


@dataclass(frozen=True, slots=True)
class CompletedProcessStub:
    returncode: int
    stdout: str
    stderr: str


def test_list_git_visible_files_deduplicates_and_sorts(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> CompletedProcessStub:
        return CompletedProcessStub(
            returncode=0,
            stdout="\ndocs/cli/guide.md\ndocs/api/index.md\ndocs/cli/guide.md\n",
            stderr="",
        )

    monkeypatch.setattr(update_docs_module.subprocess, "run", fake_run)

    result = update_docs_module._list_git_visible_files(repo_root=tmp_path)

    assert result == (Path("docs/api/index.md"), Path("docs/cli/guide.md"))


def test_build_docs_context_keeps_only_allowed_docs_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        update_docs_module,
        "_list_git_visible_files",
        lambda *, repo_root: (
            Path("docs/cli/devops.md"),
            Path("docs/api/index.md"),
            Path("docs/index.md"),
            Path("docs/assets/logo.svg"),
        ),
    )

    result = update_docs_module._build_docs_context(repo_root=tmp_path)

    assert result == "docs/cli/devops.md@-@docs/api/index.md"


def test_update_docs_writes_context_file_even_when_agent_creation_fails(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(update_docs_module, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_docs_module, "_build_docs_context", lambda *, repo_root: "docs/cli/devops.md@-@docs/api/index.md")
    monkeypatch.setattr(update_docs_module, "agents_create_impl", fake_agents_create_impl)

    with pytest.raises(RuntimeError, match="boom"):
        update_docs_module.update_docs()

    context_path = repo_root.joinpath(".ai", "agents", update_docs_module.DEFAULT_DOCS_JOB_NAME, "context.md")

    assert captured["context"] == "docs/cli/devops.md@-@docs/api/index.md"
    assert captured["prompt"] == update_docs_module.UPDATE_DOCS_PROMPT
    assert captured["output_path"] == str(
        repo_root.joinpath(".ai", "agents", update_docs_module.DEFAULT_DOCS_JOB_NAME, "layout.json")
    )
    assert context_path.read_text(encoding="utf-8") == "docs/cli/devops.md@-@docs/api/index.md"
