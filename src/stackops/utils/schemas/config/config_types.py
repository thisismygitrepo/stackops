from typing import Literal, NotRequired, TypeAlias, TypedDict


StackOpsConfigStringKey: TypeAlias = Literal["default_rclone_config", "default_email_config", "default_email_address"]


StackOpsConfig = TypedDict(
    "StackOpsConfig",
    {
        "$schema": NotRequired[str],
        "version": str,
        "default_rclone_config": NotRequired[str],
        "default_email_config": NotRequired[str],
        "default_email_address": NotRequired[str],
    },
)
