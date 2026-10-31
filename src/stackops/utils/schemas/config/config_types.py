from typing import Literal, NotRequired, TypeAlias, TypedDict

from stackops.utils.schemas.config.multiplexer_types import AgentMultiplexer, SessionMultiplexer
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


StackOpsConfigStringKey: TypeAlias = Literal["default_rclone_config", "default_email_config", "default_email_address"]


class StackOpsConfigValues(TypedDict, total=False):
    default_rclone_config: str
    default_email_config: str
    default_email_address: str
    default_agent: AGENTS
    default_session_multiplexer: SessionMultiplexer
    default_agent_multiplexer: AgentMultiplexer


_StackOpsConfigHeader = TypedDict("_StackOpsConfigHeader", {"$schema": NotRequired[str], "version": str})


class StackOpsConfig(_StackOpsConfigHeader, StackOpsConfigValues):
    pass
