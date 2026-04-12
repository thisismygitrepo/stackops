from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_qwen import fire_qwen
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, API_SPEC


def _build_ai_spec(*, machine: str) -> AI_SPEC:
    return AI_SPEC(
        provider="openai",
        model=None,
        agent="qwen",
        machine=machine,
        api_spec=API_SPEC(api_key=None, api_name="", api_label="", api_account=""),
        reasoning_effort=None,
    )


def test_fire_qwen_local_uses_quoted_prompt_path(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt with spaces.md"
    prompt_path.write_text("Prompt", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    command = fire_qwen(ai_spec=_build_ai_spec(machine="local"), prompt_path=prompt_path, repo_root=repo_root, config_dir=None)

    assert "qwen --yolo --prompt" in command
    assert str(prompt_path) in command


def test_fire_qwen_docker_requires_existing_config_dir(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Prompt", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with pytest.raises(AssertionError, match="config_dir must be provided"):
        fire_qwen(ai_spec=_build_ai_spec(machine="docker"), prompt_path=prompt_path, repo_root=repo_root, config_dir=None)

    missing_dir = tmp_path / "missing-config"
    with pytest.raises(AssertionError, match="does not exist"):
        fire_qwen(ai_spec=_build_ai_spec(machine="docker"), prompt_path=prompt_path, repo_root=repo_root, config_dir=str(missing_dir))


def test_fire_qwen_docker_mounts_expected_config_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "task.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("Prompt", encoding="utf-8")
    config_dir = tmp_path / "qwen-config"
    config_dir.mkdir()

    command = fire_qwen(ai_spec=_build_ai_spec(machine="docker"), prompt_path=prompt_path, repo_root=repo_root, config_dir=str(config_dir))

    assert "docker run -it --rm" in command
    assert f'-v "{repo_root}:/workspace/{repo_root.name}"' in command
    assert f"{config_dir / 'oauth_creds.json'}:/root/.qwen/oauth_creds.json" in command
    assert f"{config_dir / 'settings.json'}:/root/.qwen/settings.json" in command
    assert 'qwen --prompt "$PATH_PROMPT"' in command
