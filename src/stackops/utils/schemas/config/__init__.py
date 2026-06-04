CONFIG_SCHEMA_PATH_REFERENCE = "config.schema.json"

from stackops.utils.schemas.config.config_types import (
    StackOpsConfig,
    StackOpsConfigPathListKey,
    StackOpsConfigStringKey,
)

__all__ = [
    "CONFIG_SCHEMA_PATH_REFERENCE",
    "StackOpsConfig",
    "StackOpsConfigPathListKey",
    "StackOpsConfigStringKey",
]
