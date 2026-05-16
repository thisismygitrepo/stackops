from pathlib import Path

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_agents import agents_impl


def test_confirm_existing_agents_dir_cleanup_asks_before_deleting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    prompts: list[tuple[str, bool]] = []

    monkeypatch.setattr(agents_impl.sys.stdin, "isatty", lambda: True)

    def fake_confirm(message: str, default: bool) -> bool:
        prompts.append((message, default))
        return True

    monkeypatch.setattr(agents_impl.typer, "confirm", fake_confirm)

    agents_impl._confirm_existing_agents_dir_cleanup(
        agents_dir_obj=agents_dir,
    )

    assert prompts == [
        (
            f"Agents directory already exists and will be deleted to create a clean workspace:\n{agents_dir}\nContinue?",
            False,
        )
    ]


def test_confirm_existing_agents_dir_cleanup_rejects_non_interactive_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    monkeypatch.setattr(agents_impl.sys.stdin, "isatty", lambda: False)

    with pytest.raises(RuntimeError, match="Refusing to delete an existing agents directory in non-interactive mode"):
        agents_impl._confirm_existing_agents_dir_cleanup(
            agents_dir_obj=agents_dir,
        )


def test_confirm_existing_agents_dir_cleanup_aborts_when_user_declines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    monkeypatch.setattr(agents_impl.sys.stdin, "isatty", lambda: True)

    def fake_confirm(message: str, default: bool) -> bool:
        del message, default
        return False

    monkeypatch.setattr(agents_impl.typer, "confirm", fake_confirm)

    with pytest.raises(RuntimeError, match="Aborted: kept existing agents directory"):
        agents_impl._confirm_existing_agents_dir_cleanup(agents_dir_obj=agents_dir)


def test_build_parallel_yaml_entry_uses_run_parallel_shape(tmp_path: Path) -> None:
    entry = agents_impl._build_parallel_yaml_entry(
        repo_root=tmp_path,
        agent="codex",
        model="gpt-5.4",
        reasoning_effort="high",
        provider="openai",
        host="local",
        context=None,
        context_path=str(tmp_path / ".ai" / "agents" / "docs" / "context.md"),
        separator="\n@-@\n",
        agent_load=4,
        prompt=None,
        prompt_path=str(tmp_path / ".ai" / "prompts" / "update.md"),
        prompt_name=None,
        job_name="updateDocs",
        join_prompt_and_context=False,
        run=True,
        output_path=str(tmp_path / ".ai" / "agents" / "docs" / "layout.json"),
        agents_dir=str(tmp_path / ".ai" / "agents" / "docs"),
    )

    assert entry == {
        "agent": "codex",
        "model": "gpt-5.4",
        "reasoning": "high",
        "provider": "openai",
        "host": "local",
        "context": None,
        "context_path": "./.ai/agents/docs/context.md",
        "separator": "\\n@-@\\n",
        "agent_load": 4,
        "prompt": None,
        "prompt_path": "./.ai/prompts/update.md",
        "prompt_name": None,
        "job_name": "updateDocs",
        "join_prompt_and_context": False,
        "run": True,
        "output_path": "./.ai/agents/docs/layout.json",
        "agents_dir": "./.ai/agents/docs",
        "interactive": False,
    }


def test_save_parallel_yaml_entry_writes_job_name_key(tmp_path: Path) -> None:
    yaml_path = agents_impl._save_parallel_yaml_entry(
        repo_root=tmp_path,
        agent="codex",
        model=None,
        reasoning_effort=None,
        provider="openai",
        host="local",
        context="context text",
        context_path=None,
        separator="\n@-@\n",
        agent_load=3,
        prompt="prompt text",
        prompt_path=None,
        prompt_name=None,
        job_name="updateDocs",
        join_prompt_and_context=True,
        run=False,
        output_path=None,
        agents_dir=None,
    )

    loaded_yaml = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["updateDocs"]["job_name"] == "updateDocs"
    assert loaded_yaml["updateDocs"]["separator"] == "\\n@-@\\n"
    assert loaded_yaml["updateDocs"]["context"] == "context text"
    assert loaded_yaml["updateDocs"]["prompt"] == "prompt text"
    assert loaded_yaml["updateDocs"]["interactive"] is False
