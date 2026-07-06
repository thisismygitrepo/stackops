from typing import get_args

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.scripts.python.helpers.helpers_ai_account.models import ManagedLoginAgentSupport
from stackops.scripts.python.helpers.helpers_ai_account.registry import ALL_AGENT_SUPPORT, CANONICAL_AGENT_NAMES, resolve_agent_support


def test_registry_covers_every_stackops_agent_once() -> None:
    expected_agent_names = get_args(AGENTS)
    registered_agent_names = tuple(support.agent for support in ALL_AGENT_SUPPORT)

    assert CANONICAL_AGENT_NAMES == expected_agent_names
    assert registered_agent_names == expected_agent_names
    assert len(set(registered_agent_names)) == len(registered_agent_names)


def test_registry_resolves_collision_free_aliases() -> None:
    expected_aliases = {
        "a": "agy",
        "antigravity": "agy",
        "agent": "cursor-agent",
        "c": "copilot",
        "x": "codex",
        "o": "opencode",
        "omp": "opencode",
        "p": "pi",
    }

    for alias, canonical_name in expected_aliases.items():
        assert resolve_agent_support(selector=alias).agent == canonical_name


def test_secure_store_agents_have_explicit_managed_login_support() -> None:
    managed_login_agents = {
        support.agent for support in ALL_AGENT_SUPPORT if isinstance(support, ManagedLoginAgentSupport)
    }

    assert managed_login_agents == {"agy", "copilot", "oz", "droid"}
