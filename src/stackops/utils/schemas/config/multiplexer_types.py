from typing import Final, Literal, TypeAlias, cast, get_args


SessionMultiplexer: TypeAlias = Literal["tmux", "herdr", "tuios", "aoe"]
SessionMultiplexerOption: TypeAlias = Literal["tmux", "t", "herdr", "h", "tuios", "u", "aoe", "e"]
AgentMultiplexer: TypeAlias = Literal["tuios", "herdr", "aoe"]

SESSION_MULTIPLEXERS: Final[tuple[SessionMultiplexer, ...]] = cast(tuple[SessionMultiplexer, ...], get_args(SessionMultiplexer))
AGENT_MULTIPLEXERS: Final[tuple[AgentMultiplexer, ...]] = cast(tuple[AgentMultiplexer, ...], get_args(AgentMultiplexer))
