from typing import Literal, NotRequired, TypeAlias, TypedDict

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


StackOpsConfigStringKey: TypeAlias = Literal["default_rclone_config", "default_email_config", "default_email_address"]


StackOpsConfig = TypedDict(
    "StackOpsConfig",
    {
        "$schema": NotRequired[str],
        "version": str,
        "default_rclone_config": NotRequired[str],
        "default_email_config": NotRequired[str],
        "default_email_address": NotRequired[str],
        "default_agent": NotRequired[AGENTS],
    },
)
