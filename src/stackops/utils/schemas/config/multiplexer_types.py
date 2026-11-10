from typing import Final, Literal, TypeAlias, cast, get_args


SessionMultiplexer: TypeAlias = Literal["tmux", "herdr", "tuios", "aoe", "zellij"]
SessionMultiplexerOption: TypeAlias = Literal["tmux", "t", "herdr", "h", "tuios", "u", "aoe", "e", "zellij", "z"]
AgentMultiplexer: TypeAlias = Literal["tuios", "herdr", "aoe"]
AgentStatusBackend: TypeAlias = Literal[AgentMultiplexer, "t3"]
AgentLaunchBackend: TypeAlias = Literal[SessionMultiplexer, "t3"]
AgentLaunchBackendOption: TypeAlias = Literal[SessionMultiplexerOption, "t3"]

SESSION_MULTIPLEXERS: Final[tuple[SessionMultiplexer, ...]] = cast(tuple[SessionMultiplexer, ...], get_args(SessionMultiplexer))
AGENT_MULTIPLEXERS: Final[tuple[AgentMultiplexer, ...]] = cast(tuple[AgentMultiplexer, ...], get_args(AgentMultiplexer))
AGENT_LAUNCH_BACKENDS: Final[tuple[AgentLaunchBackend, ...]] = cast(tuple[AgentLaunchBackend, ...], get_args(AgentLaunchBackend))
