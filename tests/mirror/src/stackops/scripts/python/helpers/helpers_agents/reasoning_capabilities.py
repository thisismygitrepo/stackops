from __future__ import annotations

import pytest

from stackops.scripts.python.helpers.helpers_agents import reasoning_capabilities


def test_reasoning_help_formats_shortcuts_and_notes() -> None:
    assert (
        reasoning_capabilities.reasoning_help(agent="codex")
        == "n=none, l=low, m=medium, h=high, x=xhigh; actual model support can be a narrower subset"
    )
    assert reasoning_capabilities.reasoning_help(agent="cursor-agent") == ""


def test_reasoning_support_returns_declared_efforts() -> None:
    support = reasoning_capabilities.reasoning_support(agent="claude")

    assert support.efforts == ("low", "medium", "high")
    assert support.note == "actual support depends on the selected Claude model"


def test_resolve_reasoning_validates_agent_capabilities() -> None:
    assert reasoning_capabilities.resolve_reasoning(shortcut="x", agent="codex") == "xhigh"

    with pytest.raises(ValueError) as exc_info:
        reasoning_capabilities.resolve_reasoning(shortcut="x", agent="claude")

    assert str(exc_info.value) == ("agent 'claude' does not support 'x'; supported values: l=low, m=medium, h=high")
