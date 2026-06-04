from typing import Literal, NotRequired, TypeAlias, TypedDict


StackOpsGeneralStringKey: TypeAlias = Literal["rclone_config_name", "email_config_name", "to_email"]
StackOpsGeneralPathListKey: TypeAlias = Literal["repos", "scripts", "prompts"]


class StackOpsGeneralConfig(TypedDict):
    repos: list[str]
    scripts: list[str]
    prompts: NotRequired[list[str]]
    rclone_config_name: str
    email_config_name: str
    to_email: str


StackOpsConfig = TypedDict(
    "StackOpsConfig",
    {
        "$schema": NotRequired[str],
        "version": str,
        "general": StackOpsGeneralConfig,
    },
)
