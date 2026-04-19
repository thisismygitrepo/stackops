from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_pi import fire_pi
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, API_SPEC, HOST, PROVIDER, ReasoningEffort


def _build_ai_spec(*, machine: HOST, provider: PROVIDER | None, model: str | None, reasoning_effort: ReasoningEffort | None) -> AI_SPEC:
    return AI_SPEC(
        provider=provider,
        model=model,
        agent="pi",
        machine=machine,
        api_spec=API_SPEC(api_key=None, api_name="", api_label="", api_account=""),
        reasoning_effort=reasoning_effort,
    )


def test_fire_pi_local_command_includes_provider_model_and_thinking(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "task.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("prompt", encoding="utf-8")

    command = fire_pi(
        _build_ai_spec(machine="local", provider="openai", model="gpt-5.4", reasoning_effort="none"),
        prompt_path,
        repo_root,
    )

    assert "pi --provider openai --model gpt-5.4 --thinking off -p" in command
    assert '"$(cat prompts/task.md)"' in command


def test_fire_pi_docker_wraps_local_command(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "task.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("prompt", encoding="utf-8")

    command = fire_pi(
        _build_ai_spec(machine="docker", provider=None, model=None, reasoning_effort="high"),
        prompt_path,
        repo_root,
    )

    assert "docker run -it --rm" in command
    assert "pi --thinking high -p" in command
