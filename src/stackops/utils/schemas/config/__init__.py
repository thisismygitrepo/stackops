CONFIG_PATH_REFERENCE = "config.json"
CONFIG_SCHEMA_PATH_REFERENCE = "config.schema.json"

from stackops.utils.schemas.config.config_types import (
    StackOpsConfig,
    StackOpsConfigStringKey,
)

__all__ = [
    "CONFIG_PATH_REFERENCE",
    "CONFIG_SCHEMA_PATH_REFERENCE",
    "StackOpsConfig",
    "StackOpsConfigStringKey",
]
