from pathlib import Path

from stackops.utils.accessories import get_repo_root
from stackops.utils.repos.constants import WORKSPACE_REPO_MARKER, WORKSPACE_REPO_MINIMUM


def resolve_project_root(*, current_dir: Path) -> Path | None:
    directory = current_dir.expanduser().resolve()
    if not directory.is_dir():
        return None

    repo_root = get_repo_root(directory)
    if repo_root is not None:
        return repo_root.resolve()

    try:
        child_paths = tuple(directory.iterdir())
    except OSError as error:
        raise ValueError(f"""Cannot inspect workspace directory: {directory}""") from error

    nested_repo_count = 0
    for child_path in child_paths:
        if child_path.is_dir() and child_path.joinpath(WORKSPACE_REPO_MARKER).exists():
            nested_repo_count += 1
            if nested_repo_count >= WORKSPACE_REPO_MINIMUM:
                return directory
    return None
