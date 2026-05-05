from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import normalize_reasoning_effort


def test_normalize_reasoning_effort_keeps_supported_values() -> None:
    assert normalize_reasoning_effort(agent="copilot", reasoning_effort="high") == "high"


def test_normalize_reasoning_effort_drops_unsupported_values() -> None:
    assert normalize_reasoning_effort(agent="claude", reasoning_effort="high") is None
