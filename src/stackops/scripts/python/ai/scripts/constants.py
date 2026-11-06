from typing import Final, Literal

type CheckerName = Literal["pyright", "mypy", "pylint", "pyrefly", "ty", "ruff"]

TYPE_CHECK_TOOLS_ENV_VAR: Final[str] = "STACKOPS_TYPE_CHECK_TOOLS"
TYPE_CHECK_TOOL_NAMES: Final[tuple[CheckerName, ...]] = (
    "pyright",
    "mypy",
    "pylint",
    "pyrefly",
    "ty",
    "ruff",
)
