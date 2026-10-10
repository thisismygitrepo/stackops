from typing import Final

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH, read_stackops_config

_BUILTIN_DEFAULT_AGENT: Final[AGENTS] = "codex"
DEFAULT_AGENT_HELP: Final[str] = f"Defaults to `default_agent` in {DOTFILES_STACKOPS_CONFIG_PATH}, else {_BUILTIN_DEFAULT_AGENT}."


def resolve_agent(agent: AGENTS | None) -> AGENTS:
    if agent is not None:
        return agent
    if not DOTFILES_STACKOPS_CONFIG_PATH.exists():
        return _BUILTIN_DEFAULT_AGENT
    return read_stackops_config().get("default_agent", _BUILTIN_DEFAULT_AGENT)
