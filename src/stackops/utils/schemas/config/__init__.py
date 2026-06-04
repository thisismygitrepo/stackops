CONFIG_SCHEMA_PATH_REFERENCE = "config.schema.json"

from stackops.utils.schemas.config.config_types import (
    StackOpsConfig,
    StackOpsConnectionProfile,
    StackOpsGeneralConfig,
    StackOpsGeneralPathListKey,
    StackOpsGeneralStringKey,
    StackOpsWifiConnectionProfile,
)

__all__ = [
    "CONFIG_SCHEMA_PATH_REFERENCE",
    "StackOpsConfig",
    "StackOpsConnectionProfile",
    "StackOpsGeneralConfig",
    "StackOpsGeneralPathListKey",
    "StackOpsGeneralStringKey",
    "StackOpsWifiConnectionProfile",
]
