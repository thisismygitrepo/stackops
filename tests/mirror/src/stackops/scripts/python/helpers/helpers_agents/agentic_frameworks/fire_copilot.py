from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot import fire_copilot
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC


def _build_ai_spec(*, machine: str, model: str | None) -> AI_SPEC:
    return cast(
        AI_SPEC,
        {
            "machine": machine,
            "api_spec": {"api_key": None},
            "model": model,
        },
    )


def test_fire_copilot_local_command_reads_prompt_and_passes_model(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"

    command = fire_copilot(_build_ai_spec(machine="local", model="gpt-5.4"), prompt_path, repo_root)

    assert 'copilot -p "$(cat prompts/agent.md)" --model gpt-5.4 --yolo' in command


def test_fire_copilot_docker_command_mounts_repo_and_omits_blank_model(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"

    command = fire_copilot(_build_ai_spec(machine="docker", model=None), prompt_path, repo_root)

    assert "docker run -it --rm" in command
    assert f'-v "{repo_root}:/workspace/{repo_root.name}"' in command
    assert '$(cat prompts/agent.md)' in command
    assert "--model" not in command
