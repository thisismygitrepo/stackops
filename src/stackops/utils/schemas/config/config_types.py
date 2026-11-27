from typing import Literal, Required, TypeAlias, TypedDict

from stackops.utils.schemas.config.multiplexer_types import AgentMultiplexer, SessionMultiplexer
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


StackOpsConfigStringKey: TypeAlias = Literal["default_rclone_config"]


class StackOpsConfigValues(TypedDict, total=False):
    default_rclone_config: str
    default_agent: AGENTS
    default_session_multiplexer: SessionMultiplexer
    default_agent_multiplexer: AgentMultiplexer


class StackOpsConfig(StackOpsConfigValues):
    version: Required[str]
