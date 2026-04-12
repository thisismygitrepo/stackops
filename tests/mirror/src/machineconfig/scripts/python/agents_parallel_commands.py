import importlib
import sys
import types
from pathlib import Path

import pytest
import typer

commands_module = importlib.import_module("machineconfig.scripts.python.agents_parallel_commands")


def test_decode_separator_unescapes_newline() -> None:
    assert commands_module._decode_separator(separator=r"\n") == "\n"


def test_agents_create_passes_decoded_separator(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake_agents_impl = types.ModuleType("machineconfig.scripts.python.helpers.helpers_agents.agents_impl")

    def fake_impl(**kwargs: object) -> None:
        captured.update(kwargs)

    fake_agents_impl.agents_create = fake_impl
    monkeypatch.setitem(
        sys.modules,
        "machineconfig.scripts.python.helpers.helpers_agents.agents_impl",
        fake_agents_impl,
    )

    commands_module.agents_create(
        agent="codex",
        model=None,
        reasoning_effort=None,
        provider=None,
        host="local",
        context=None,
        context_path=None,
        separator=r"\n",
        agent_load=2,
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name="job",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        interactive=False,
    )

    assert captured["separator"] == "\n"
    assert captured["agent_load"] == 2


def test_agents_create_wraps_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_agents_impl = types.ModuleType("machineconfig.scripts.python.helpers.helpers_agents.agents_impl")

    def fake_impl(**kwargs: object) -> None:
        raise ValueError("bad separator")

    fake_agents_impl.agents_create = fake_impl
    monkeypatch.setitem(
        sys.modules,
        "machineconfig.scripts.python.helpers.helpers_agents.agents_impl",
        fake_agents_impl,
    )

    with pytest.raises(typer.BadParameter, match="bad separator"):
        commands_module.agents_create(
            agent="codex",
            model=None,
            reasoning_effort=None,
            provider=None,
            host="local",
            context=None,
            context_path=None,
            separator=",",
            agent_load=1,
            prompt=None,
            prompt_path=None,
            prompt_name=None,
            job_name="job",
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            interactive=False,
        )


def test_create_context_appends_instruction_and_writes_separator_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake_run_impl_module = types.ModuleType("machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl")

    def fake_run(**kwargs: object) -> None:
        captured.update(kwargs)

    fake_run_impl_module.run = fake_run
    monkeypatch.setitem(
        sys.modules,
        "machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl",
        fake_run_impl_module,
    )
    monkeypatch.chdir(tmp_path)

    commands_module.create_context(
        prompt="summarize repo",
        job_name="demo_job",
        agent="copilot",
        separator=r"\n--\n",
    )

    separator_path = tmp_path / ".ai" / "agents" / "demo_job" / "separator.txt"

    assert str(captured["agent"]) == "copilot"
    assert "summarize repo" in str(captured["prompt"])
    assert "\n--\n" in str(captured["prompt"])
    assert separator_path.read_text(encoding="utf-8") == r"\n--\n"
