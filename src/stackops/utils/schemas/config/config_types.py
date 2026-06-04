from typing import Literal, NotRequired, TypeAlias, TypedDict


StackOpsConfigStringKey: TypeAlias = Literal["rclone_config_name", "email_config_name", "to_email"]
StackOpsConfigPathListKey: TypeAlias = Literal["repos"]


StackOpsConfig = TypedDict(
    "StackOpsConfig",
    {
        "$schema": NotRequired[str],
        "version": str,
        "repos": list[str],
        "rclone_config_name": str,
        "email_config_name": str,
        "to_email": str,
    },
)
