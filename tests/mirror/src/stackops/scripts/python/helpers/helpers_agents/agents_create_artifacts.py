from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_create_artifacts


def test_write_create_artifacts_writes_powershell_recreate_script_on_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(agents_create_artifacts.agent_shell, "is_windows_host", lambda: True)

    output = agents_create_artifacts.write_create_artifacts(
        repo_root=tmp_path,
        agents_dir=tmp_path / "agents",
        layout_output_path=tmp_path / "layout.json",
        agent="gemini",
        host="local",
        model="gemini-2.5-pro",
        reasoning_effort=None,
        provider="google",
        agent_load=1,
        separator="\n@-@\n",
        prompt=agents_create_artifacts.CreatePromptArtifactsInput(
            source_kind="inline_text", source_path=None, source_name=None, content="prompt text"
        ),
        context=agents_create_artifacts.CreateContextArtifactsInput(
            source_kind="inline_text", source_path=None, file_content="context text", directory_entries=()
        ),
        job_name="job",
        join_prompt_and_context=False,
        run=False,
    )

    payload = output.recreate_script_path.read_text(encoding="utf-8")

    assert output.recreate_script_path.name == "recreate_layout.ps1"
    assert "$ErrorActionPreference = 'Stop'" in payload
    assert "Set-Location -LiteralPath" in payload
    assert "uv 'run' 'agents' 'parallel' 'create'" in payload
    assert "#!/usr/bin/env bash" not in payload


def test_write_create_artifacts_writes_multiline_recreate_script_on_posix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(agents_create_artifacts.agent_shell, "is_windows_host", lambda: False)

    output = agents_create_artifacts.write_create_artifacts(
        repo_root=tmp_path,
        agents_dir=tmp_path / "agents",
        layout_output_path=tmp_path / "layout.json",
        agent="codex",
        host="local",
        model=None,
        reasoning_effort="high",
        provider="openai",
        agent_load=3,
        stutter_max=4.25,
        separator="\n@-@\n",
        prompt=agents_create_artifacts.CreatePromptArtifactsInput(
            source_kind="file_path", source_path=tmp_path / "prompt.md", source_name=None, content="prompt text"
        ),
        context=agents_create_artifacts.CreateContextArtifactsInput(
            source_kind="file_path", source_path=tmp_path / "context.md", file_content="context text", directory_entries=()
        ),
        job_name="job",
        join_prompt_and_context=False,
        run=False,
    )

    payload = output.recreate_script_path.read_text(encoding="utf-8")

    assert output.recreate_script_path.name == "recreate_layout.sh"
    assert "#!/usr/bin/env bash" in payload
    assert f"cd {tmp_path} && \\" in payload
    assert "    uv run agents parallel create \\" in payload
    assert "    --agent codex \\" in payload
    assert "    --stutter-max 4.25 \\" in payload
    assert "    --prompt-path prompt.md \\" in payload
    assert "    --context-path context.md \\" in payload
    assert "    --job-name job" in payload
