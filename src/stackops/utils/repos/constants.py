from typing import Final


WORKSPACE_REPO_MARKER: Final[str] = ".git"
WORKSPACE_REPO_MINIMUM: Final[int] = 2
PROJECT_ROOT_REQUIREMENT: Final[str] = (
    "running inside a git repository (including a monorepo) or from a workspace directory "
    "containing at least two immediate child git repositories"
)
