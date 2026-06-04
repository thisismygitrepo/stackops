CONFIG_SCHEMA_PATH_REFERENCE = "config.schema.json"

from stackops.utils.schemas.config.config_types import (
    StackOpsConfig,
    StackOpsGeneralConfig,
    StackOpsGeneralPathListKey,
    StackOpsGeneralStringKey,
)

__all__ = [
    "CONFIG_SCHEMA_PATH_REFERENCE",
    "StackOpsConfig",
    "StackOpsGeneralConfig",
    "StackOpsGeneralPathListKey",
    "StackOpsGeneralStringKey",
]
