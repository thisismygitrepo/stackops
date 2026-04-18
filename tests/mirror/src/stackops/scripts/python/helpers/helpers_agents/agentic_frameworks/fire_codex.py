from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex import fire_codex
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC


def _build_ai_spec(*, machine: str, api_key: str | None, model: str | None, reasoning_effort: str | None) -> AI_SPEC:
    return cast(AI_SPEC, {"machine": machine, "api_spec": {"api_key": api_key}, "model": model, "reasoning_effort": reasoning_effort})


def test_fire_codex_local_command_includes_model_reasoning_and_api_key(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"

    command = fire_codex(_build_ai_spec(machine="local", api_key="sk-test", model="gpt-5.4", reasoning_effort="high"), prompt_path, repo_root)

    assert 'export CODEX_API_KEY="sk-test"' in command
    assert "--model gpt-5.4" in command
    assert 'model_reasoning_effort="high"' in command
    assert "< prompts/agent.md" in command


def test_fire_codex_warns_without_api_key_and_builds_docker_command(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"

    local_command = fire_codex(_build_ai_spec(machine="local", api_key=None, model=None, reasoning_effort=None), prompt_path, repo_root)
    docker_command = fire_codex(_build_ai_spec(machine="docker", api_key="sk-docker", model=None, reasoning_effort=None), prompt_path, repo_root)

    assert "Warning: No CODEX_API_KEY provided" in local_command
    assert "--model" not in local_command
    assert "docker run -it --rm" in docker_command
    assert "-e CODEX_API_KEY=sk-docker" in docker_command
    assert f'-v "{repo_root}:/workspace/{repo_root.name}"' in docker_command
