from typing import Literal, NotRequired, TypeAlias, TypedDict


StackOpsConfigStringKey: TypeAlias = Literal["rclone_config_name", "email_config_name", "to_email"]


StackOpsConfig = TypedDict(
    "StackOpsConfig",
    {
        "$schema": NotRequired[str],
        "version": str,
        "rclone_config_name": str,
        "email_config_name": str,
        "to_email": str,
    },
)
