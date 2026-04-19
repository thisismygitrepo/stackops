

from typing import get_args

from stackops.scripts.python.helpers.helpers_agents import fire_agents_helper_types as module


def test_public_literals_and_prompt_separator_remain_stable() -> None:
    assert "codex" in get_args(module.AGENTS)
    assert "warp-cli" in get_args(module.AGENTS)
    assert get_args(module.PROVIDER) == (
        "azure",
        "google",
        "aws",
        "openai",
        "anthropic",
        "openrouter",
        "xai",
    )
    assert get_args(module.ReasoningEffort) == ("none", "low", "medium", "high", "xhigh")
    assert "keyword_search" in get_args(module.SEARCH_STRATEGIES)
    assert module.DEFAULT_SEAPRATOR.join(("task-1", "task-2")).split(module.DEFAULT_SEAPRATOR) == ["task-1", "task-2"]
    assert module.AGENT_NAME_FORMATTER.format(idx=21) == "agent_21_cmd.sh"
