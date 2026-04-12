from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.fire_agents_help_launch as launch_module


def test_get_api_keys_reads_ini_and_skips_empty_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api_key_path = tmp_path / "dotfiles" / "creds" / "llm" / "openai" / "api_keys.ini"
    api_key_path.parent.mkdir(parents=True)
    api_key_path.write_text(
        "[primary]\napi_key = live-key\napi_name = Main\nemail = one@example.com\n\n[empty]\napi_key =\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(launch_module.Path, "home", lambda: tmp_path)

    api_keys = launch_module.get_api_keys("openai", silent_if_missing=False)

    assert api_keys == [
        {
            "api_key": "live-key",
            "api_name": "Main",
            "api_label": "primary",
            "api_account": "one@example.com",
        }
    ]


def test_prep_agent_launch_writes_prompt_material_and_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    agents_dir = repo_root / ".ai" / "agents" / "job"
    repo_root.mkdir()

    monkeypatch.setattr(launch_module.random, "uniform", lambda _start, _end: 0.0)
    monkeypatch.setattr(launch_module, "_build_generic_agent_command", lambda **_kwargs: "cursor-agent --run")

    launch_module.prep_agent_launch(
        repo_root=repo_root,
        agents_dir=agents_dir,
        prompts_material=["first material"],
        prompt_prefix="Prefix text",
        join_prompt_and_context=False,
        machine="local",
        model=None,
        reasoning_effort=None,
        provider=None,
        agent="cursor-agent",
        job_name="job",
    )

    prompt_root = agents_dir / "prompts" / "agent_0"
    prompt_text = (prompt_root / "agent_0_prompt.txt").read_text(encoding="utf-8")
    material_text = (prompt_root / "agent_0_material.txt").read_text(encoding="utf-8")
    launcher_text = (prompt_root / "agent_0_cmd.sh").read_text(encoding="utf-8")

    assert "Please only look @ .ai/agents/job/prompts/agent_0/agent_0_material.txt." in prompt_text
    assert material_text == "first material"
    assert 'export FIRE_AGENTS_PROMPT_FILE="' in launcher_text
    assert "Sleeping for 0.00 seconds" in launcher_text
    assert "cursor-agent --run" in launcher_text


def test_get_agents_launch_layout_sorts_agents_numerically(tmp_path: Path) -> None:
    session_root = tmp_path / ".ai" / "agents" / "job"
    for name in ("agent_10", "agent_2", "agent_1"):
        agent_dir = session_root / "prompts" / name
        agent_dir.mkdir(parents=True)
        (agent_dir / f"{name}_cmd.sh").write_text("echo run\n", encoding="utf-8")

    layout = launch_module.get_agents_launch_layout(session_root, job_name="job")

    tab_names = [tab["tabName"] for tab in layout["layouts"][0]["layoutTabs"]]
    commands = [tab["command"] for tab in layout["layouts"][0]["layoutTabs"]]
    assert tab_names == ["Agent1", "Agent2", "Agent10"]
    assert commands[0].endswith("agent_1/agent_1_cmd.sh")
    assert layout["layouts"][0]["layoutTabs"][0]["startDir"] == str(tmp_path)
