import platform
from typing import Final

from stackops.utils.schemas.config.multiplexer_types import AgentMultiplexer, SessionMultiplexer, SessionMultiplexerOption
from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH, read_stackops_config

BUILTIN_DEFAULT_SESSION_MULTIPLEXER: Final[SessionMultiplexer] = "tmux"
BUILTIN_DEFAULT_AGENT_MULTIPLEXER: Final[AgentMultiplexer] = "tuios"
DEFAULT_SESSION_MULTIPLEXER_HELP: Final[str] = (
    f"Defaults to `default_session_multiplexer` in {DOTFILES_STACKOPS_CONFIG_PATH}, else {BUILTIN_DEFAULT_SESSION_MULTIPLEXER}."
)
DEFAULT_AGENT_MULTIPLEXER_HELP: Final[str] = (
    f"Defaults to `default_agent_multiplexer` in {DOTFILES_STACKOPS_CONFIG_PATH}, else {BUILTIN_DEFAULT_AGENT_MULTIPLEXER}."
)


def _require_supported_platform(multiplexer: SessionMultiplexer) -> None:
    if multiplexer in ("herdr", "aoe") and platform.system() == "Windows":
        raise ValueError(f"The {multiplexer} multiplexer requires macOS or Linux.")


def resolve_session_multiplexer(multiplexer: SessionMultiplexerOption | None) -> SessionMultiplexer:
    resolved: SessionMultiplexer
    match multiplexer:
        case None if DOTFILES_STACKOPS_CONFIG_PATH.exists():
            resolved = read_stackops_config().get("default_session_multiplexer", BUILTIN_DEFAULT_SESSION_MULTIPLEXER)
        case None:
            resolved = BUILTIN_DEFAULT_SESSION_MULTIPLEXER
        case "tmux" | "t":
            resolved = "tmux"
        case "herdr" | "h":
            resolved = "herdr"
        case "tuios" | "u":
            resolved = "tuios"
        case "aoe" | "e":
            resolved = "aoe"
    _require_supported_platform(multiplexer=resolved)
    return resolved


def resolve_agent_multiplexer(multiplexer: AgentMultiplexer | None) -> AgentMultiplexer:
    resolved: AgentMultiplexer
    match multiplexer:
        case None if DOTFILES_STACKOPS_CONFIG_PATH.exists():
            resolved = read_stackops_config().get("default_agent_multiplexer", BUILTIN_DEFAULT_AGENT_MULTIPLEXER)
        case None:
            resolved = BUILTIN_DEFAULT_AGENT_MULTIPLEXER
        case _:
            resolved = multiplexer
    _require_supported_platform(multiplexer=resolved)
    return resolved
