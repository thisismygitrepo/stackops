from pathlib import Path

import pytest
import typer

from stackops.scripts.python.helpers.helpers_utils import test_runtime


def test_collect_python_files_skips_hidden_paths_and_venv(tmp_path: Path) -> None:
    search_root = tmp_path / "workspace"
    search_root.mkdir()
    search_root.joinpath("keep.py").write_text("""print("keep")\n""", encoding="utf-8")
    search_root.joinpath("nested").mkdir()
    search_root.joinpath("nested/module.py").write_text("""print("nested")\n""", encoding="utf-8")
    search_root.joinpath(".hidden.py").write_text("""print("hidden file")\n""", encoding="utf-8")
    search_root.joinpath(".hidden_dir").mkdir()
    search_root.joinpath(".hidden_dir/ignored.py").write_text("""print("hidden dir")\n""", encoding="utf-8")
    search_root.joinpath(".venv").mkdir()
    search_root.joinpath(".venv/ignored.py").write_text("""print("venv")\n""", encoding="utf-8")

    collected_paths = test_runtime._collect_python_files(search_root=search_root)

    assert [path.relative_to(search_root).as_posix() for path in collected_paths] == [
        "keep.py",
        "nested/module.py",
    ]


def test_write_context_file_uses_repo_relative_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    search_root = repo_root / "src"
    search_root.mkdir(parents=True)
    search_root.joinpath("app.py").write_text("""print("app")\n""", encoding="utf-8")
    search_root.joinpath("pkg").mkdir()
    search_root.joinpath("pkg/mod.py").write_text("""print("mod")\n""", encoding="utf-8")
    context_path = repo_root / ".ai" / "agents" / test_runtime.JOB_NAME / "context.md"

    file_count = test_runtime._write_context_file(
        repo_root=repo_root,
        search_root=search_root,
        context_path=context_path,
    )

    assert file_count == 2
    context_chunks = context_path.read_text(encoding="utf-8").split(test_runtime.FILE_SEPARATOR)
    assert len(context_chunks) == 2
    assert "repo_relative_path: src/app.py" in context_chunks[0]
    assert "repo_relative_path: src/pkg/mod.py" in context_chunks[1]


def test_launch_test_runtime_builds_context_and_runs_agents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    search_root = repo_root / "src"
    search_root.mkdir(parents=True)
    search_root.joinpath("feature.py").write_text("""print("feature")\n""", encoding="utf-8")
    search_root.joinpath("pkg").mkdir()
    search_root.joinpath("pkg/logic.py").write_text("""print("logic")\n""", encoding="utf-8")
    monkeypatch.chdir(search_root)

    captured_agents_create: dict[str, object] = {}
    captured_terminal_run: dict[str, object] = {}

    def fake_get_repo_root(_path: Path) -> Path:
        return repo_root

    def fake_agents_create_command(**kwargs: object) -> None:
        captured_agents_create.update(kwargs)

    def fake_terminal_run_command(**kwargs: object) -> None:
        captured_terminal_run.update(kwargs)

    monkeypatch.setattr(test_runtime, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(test_runtime, "agents_create_command", fake_agents_create_command)
    monkeypatch.setattr(test_runtime, "terminal_run_command", fake_terminal_run_command)
    monkeypatch.setattr(test_runtime.typer, "confirm", lambda message, default: True)

    ctx = typer.Context(typer.main.get_command(test_runtime.get_app()))
    test_runtime.launch_test_runtime(ctx=ctx, agent="codex", agent_load=2, max_tabs=4)

    assert captured_agents_create["agent"] == "codex"
    assert captured_agents_create["agent_load"] == 2
    assert captured_agents_create["job_name"] == test_runtime.JOB_NAME
    assert captured_agents_create["separator"] == test_runtime.FILE_SEPARATOR
    assert captured_agents_create["prompt"] == test_runtime._build_prompt(repo_name=repo_root.name)
    raw_context_path = captured_agents_create["context_path"]
    assert isinstance(raw_context_path, str)
    context_path = Path(raw_context_path)
    assert context_path.is_file()
    context_text = context_path.read_text(encoding="utf-8")
    assert "repo_relative_path: src/feature.py" in context_text
    assert "repo_relative_path: src/pkg/logic.py" in context_text
    assert captured_terminal_run == {
        "ctx": ctx,
        "layouts_file": test_runtime._get_layout_path(repo_root=repo_root),
        "max_tabs": 4,
        "on_conflict": "restart",
    }
