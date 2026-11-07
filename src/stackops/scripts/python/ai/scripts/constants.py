from typing import Final, Literal

type CheckerName = Literal["pyright", "mypy", "pylint", "pyrefly", "ty", "ruff"]
type ToolVersionMode = Literal["latest", "upgrade", "pinned"]

TYPE_CHECK_TOOLS_ENV_VAR: Final[str] = "STACKOPS_TYPE_CHECK_TOOLS"
TYPE_CHECK_TOOL_VERSIONS_ENV_VAR: Final[str] = "STACKOPS_TYPE_CHECK_TOOL_VERSIONS"
DEFAULT_TOOL_VERSION_MODE: Final[ToolVersionMode] = "latest"
TOOL_VERSION_MODES: Final[tuple[ToolVersionMode, ...]] = ("latest", "upgrade", "pinned")
TYPE_CHECK_TOOL_NAMES: Final[tuple[CheckerName, ...]] = (
    "pyright",
    "mypy",
    "pylint",
    "pyrefly",
    "ty",
    "ruff",
)
