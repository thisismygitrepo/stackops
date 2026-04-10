import pytest

from machineconfig.scripts.python.helpers.helpers_agents import agents_create_inputs as inputs_module
from machineconfig.scripts.python.helpers.helpers_agents.agents_create_inputs import resolve_prompt_input


def test_resolve_prompt_input_supports_prompt_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_resolve_named_prompts_yaml_entry(*, prompts_yaml_path: str | None, entry_name: str, where: str, entry_label: str) -> str:
        assert prompts_yaml_path is None
        assert entry_name == "team.backend"
        assert where == "all"
        assert entry_label == "Prompt name"
        return "resolved prompt"

    monkeypatch.setattr(inputs_module, "resolve_named_prompts_yaml_entry", fake_resolve_named_prompts_yaml_entry)

    resolved = resolve_prompt_input(prompt=None, prompt_path=None, prompt_name="team.backend")

    assert resolved.prompt_text == "resolved prompt"
    assert resolved.source_kind == "yaml_name"
    assert resolved.source_path is None
    assert resolved.source_name == "team.backend"


def test_resolve_prompt_input_requires_exactly_one_prompt_source() -> None:
    with pytest.raises(ValueError, match="Exactly one of --prompt, --prompt-path, or --prompt-name must be provided"):
        resolve_prompt_input(prompt="prompt body", prompt_path=None, prompt_name="team.backend")
