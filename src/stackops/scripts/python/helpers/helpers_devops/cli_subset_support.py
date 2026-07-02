from pathlib import Path
from typing import Literal


type SubsetOutputConflictAction = Literal["throw-error", "overwrite", "append"]
type SubsetOutputConflictOption = Literal["throw-error", "t", "overwrite", "o", "append", "a"]
SUBSET_OUTPUT_CONFLICT_ACTIONS: dict[SubsetOutputConflictOption, SubsetOutputConflictAction] = {
    "throw-error": "throw-error",
    "t": "throw-error",
    "overwrite": "overwrite",
    "o": "overwrite",
    "append": "append",
    "a": "append",
}


def resolve_subset_output_path(output_path: Path) -> Path:
    expanded_path = output_path.expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path
