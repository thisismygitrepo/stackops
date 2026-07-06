from types import MappingProxyType
from typing import Final, cast, get_args

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.scripts.python.helpers.helpers_ai_account.agy import SUPPORT as AGY_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.auggie import SUPPORT as AUGGIE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.claude import SUPPORT as CLAUDE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.cline import SUPPORT as CLINE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.codex import SUPPORT as CODEX_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.copilot import SUPPORT as COPILOT_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.crush import SUPPORT as CRUSH_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.cursor_agent import SUPPORT as CURSOR_AGENT_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.droid import SUPPORT as DROID_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.forge import SUPPORT as FORGE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.kilocode import SUPPORT as KILOCODE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.models import AgentSupport
from stackops.scripts.python.helpers.helpers_ai_account.opencode import SUPPORT as OPENCODE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.oz import SUPPORT as OZ_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.pi import SUPPORT as PI_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.q import SUPPORT as Q_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.qwen import SUPPORT as QWEN_SUPPORT


CANONICAL_AGENT_NAMES: Final[tuple[AGENTS, ...]] = cast(tuple[AGENTS, ...], get_args(AGENTS))
ALL_AGENT_SUPPORT: Final[tuple[AgentSupport, ...]] = (
    AGY_SUPPORT,
    CURSOR_AGENT_SUPPORT,
    CLAUDE_SUPPORT,
    QWEN_SUPPORT,
    COPILOT_SUPPORT,
    CODEX_SUPPORT,
    FORGE_SUPPORT,
    CRUSH_SUPPORT,
    Q_SUPPORT,
    OPENCODE_SUPPORT,
    KILOCODE_SUPPORT,
    CLINE_SUPPORT,
    AUGGIE_SUPPORT,
    OZ_SUPPORT,
    DROID_SUPPORT,
    PI_SUPPORT,
)


def _build_support_registry(supports: tuple[AgentSupport, ...]) -> MappingProxyType[str, AgentSupport]:
    support_by_canonical_name = {support.agent: support for support in supports}
    expected_agents = set(CANONICAL_AGENT_NAMES)
    actual_agents = set(support_by_canonical_name)
    if len(support_by_canonical_name) != len(supports):
        raise ValueError("Every canonical agent must have exactly one support module")
    if actual_agents != expected_agents:
        missing_agents = sorted(expected_agents - actual_agents)
        unexpected_agents = sorted(actual_agents - expected_agents)
        raise ValueError(f"Agent support registry mismatch: missing={missing_agents}, unexpected={unexpected_agents}")

    support_by_selector: dict[str, AgentSupport] = dict(support_by_canonical_name)
    for support in supports:
        for alias in support.aliases:
            if alias in support_by_selector:
                conflicting_agent = support_by_selector[alias].agent
                raise ValueError(f"Agent selector {alias!r} conflicts between {conflicting_agent} and {support.agent}")
            support_by_selector[alias] = support
    return MappingProxyType(support_by_selector)


SUPPORT_BY_SELECTOR: Final[MappingProxyType[str, AgentSupport]] = _build_support_registry(ALL_AGENT_SUPPORT)
SUPPORTED_AGENT_HELP: Final[str] = ", ".join(CANONICAL_AGENT_NAMES)


def resolve_agent_support(selector: str) -> AgentSupport:
    support = SUPPORT_BY_SELECTOR.get(selector)
    if support is None:
        raise ValueError(f"Unsupported agent: {selector}. Supported agents: {SUPPORTED_AGENT_HELP}")
    return support
