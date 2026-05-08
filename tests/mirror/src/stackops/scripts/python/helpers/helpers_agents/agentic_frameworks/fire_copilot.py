from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_copilot import fire_copilot
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, API_SPEC


def test_fire_copilot_uses_copilot_reasoning_effort_flag(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("test", encoding="utf-8")
    api_spec: API_SPEC = {
        "api_key": None,
        "api_name": "",
        "api_label": "",
        "api_account": "",
    }
    ai_spec: AI_SPEC = {
        "provider": "openai",
        "model": None,
        "agent": "copilot",
        "machine": "local",
        "api_spec": api_spec,
        "reasoning_effort": "high",
    }

    command_line = fire_copilot(ai_spec=ai_spec, prompt_path=prompt_path, repo_root=tmp_path)

    assert "--reasoning-effort high" in command_line
    assert "--reasoning high" not in command_line
