import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_t3_launch
from stackops.scripts.python.helpers.helpers_agents.agents_t3_mcp import JsonObject
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, ReasoningEffort


def _reasoning_option(option_id: str, choices: list[str]) -> JsonObject:
    return {"id": option_id, "label": "Reasoning", "type": "select", "options": [{"id": choice, "label": choice} for choice in choices]}


CAPABILITIES: JsonObject = {
    "runtimeMode": "full-access",
    "providers": [
        {
            "providerInstanceId": "codex",
            "driverKind": "codex",
            "models": [{"id": "gpt-5.6-luna", "options": [_reasoning_option("reasoningEffort", ["low", "medium", "high", "xhigh", "max"])]}],
        },
        {
            "providerInstanceId": "claudeAgent",
            "driverKind": "claudeAgent",
            "models": [
                {"id": "claude-opus-5-5", "options": [_reasoning_option("effort", ["low", "medium", "high"]), {"id": "fastMode", "options": []}]},
                {"id": "claude-haiku-5-5", "options": []},
            ],
        },
    ],
}


@pytest.mark.parametrize(
    ("agent", "model", "reasoning", "expected"),
    [
        ("claude", "claude-opus-5-5", "high", {"instanceId": "claudeAgent", "model": "claude-opus-5-5", "options": [{"id": "effort", "value": "high"}]}),
        ("codex", "gpt-5.6-luna", "xhigh", {"instanceId": "codex", "model": "gpt-5.6-luna", "options": [{"id": "reasoningEffort", "value": "xhigh"}]}),
        ("claude", "claude-haiku-5-5", None, {"instanceId": "claudeAgent", "model": "claude-haiku-5-5"}),
    ],
)
def test_model_selection_maps_agent_model_and_reasoning(agent: AGENTS, model: str, reasoning: ReasoningEffort | None, expected: JsonObject) -> None:
    target = agents_t3_launch.resolve_t3_launch_target(agent=agent, host="local", provider=None, model=model, reasoning_effort=reasoning)
    assert agents_t3_launch._model_selection(capabilities=CAPABILITIES, target=target) == expected


@pytest.mark.parametrize(
    ("model", "reasoning", "message"),
    [
        ("nope", None, "has no model 'nope'"),
        ("claude-haiku-5-5", "high", "has no reasoning option"),
        ("claude-opus-5-5", "xhigh", "not 'xhigh'"),
    ],
)
def test_model_selection_rejects_unavailable_choices(model: str, reasoning: ReasoningEffort | None, message: str) -> None:
    target = agents_t3_launch.resolve_t3_launch_target(agent="claude", host="local", provider=None, model=model, reasoning_effort=reasoning)
    with pytest.raises(ValueError, match=message):
        agents_t3_launch._model_selection(capabilities=CAPABILITIES, target=target)


def test_model_selection_requires_one_provider_instance() -> None:
    target = agents_t3_launch.resolve_t3_launch_target(agent="pi", host="local", provider=None, model="default", reasoning_effort=None)
    with pytest.raises(RuntimeError, match="Expected one T3 Code provider instance for pi, found 0"):
        agents_t3_launch._model_selection(capabilities=CAPABILITIES, target=target)
