from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import fire_agents_help_launch
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import API_SPEC


def test_prep_agent_launch_writes_powershell_launcher_on_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    api_spec: API_SPEC = {
        "api_key": "secret-key",
        "api_name": "primary",
        "api_label": "work",
        "api_account": "user@example.com",
    }
    monkeypatch.setattr(fire_agents_help_launch.agent_shell, "is_windows_host", lambda: True)
    monkeypatch.setattr(
        fire_agents_help_launch,
        "get_api_keys",
        lambda provider, silent_if_missing=False: [api_spec],
    )

    agents_dir = tmp_path / "agents"
    fire_agents_help_launch.prep_agent_launch(
        repo_root=tmp_path,
        agents_dir=agents_dir,
        prompts_material=["context block"],
        prompt_prefix="prompt block",
        join_prompt_and_context=False,
        machine="local",
        model="gemini-2.5-pro",
        reasoning_effort=None,
        provider="google",
        agent="gemini",
        job_name="job",
    )

    launcher_path = agents_dir / "prompts" / "agent_0" / "agent_0_cmd.ps1"
    payload = launcher_path.read_text(encoding="utf-8")

    assert launcher_path.exists()
    assert "$ErrorActionPreference = 'Stop'" in payload
    assert "$env:GEMINI_API_KEY = 'secret-key'" in payload
    assert "Start-Sleep -Seconds" in payload
    assert "gemini --model 'gemini-2.5-pro' --yolo --prompt" in payload
    assert "#!/usr/bin/env bash" not in payload


def test_get_agents_launch_layout_uses_powershell_runner_on_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(fire_agents_help_launch.agent_shell, "is_windows_host", lambda: True)

    prompt_dir = tmp_path / "prompts" / "agent_0"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    launcher_path = prompt_dir / "agent_0_cmd.ps1"
    launcher_path.write_text("Write-Output 'hello'\n", encoding="utf-8")

    layouts_file = fire_agents_help_launch.get_agents_launch_layout(
        session_root=tmp_path,
        job_name="job",
        start_dir=tmp_path,
    )

    command = layouts_file["layouts"][0]["layoutTabs"][0]["command"]

    assert command.startswith("pwsh ")
    assert "-File" in command
    assert "bash" not in command
    assert str(launcher_path) in command