from pathlib import Path
from typing import Final, Literal, TypeAlias

from stackops.utils.accessories import get_repo_root


REPO_STACKOPS_DIRECTORY_NAME: Final[str] = ".stackops"
REPO_PROMPTS_YAML_FILE_NAME: Final[str] = "prompts.yaml"
REPO_MCP_JSON_FILE_NAME: Final[str] = "mcp.json"
REPO_SCRIPTS_DIRECTORY_NAME: Final[str] = "scripts"

RepoStackopsPathKind: TypeAlias = Literal["prompts_yaml", "mcp_json", "scripts"]


def current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path | None:
    repo_root = get_repo_root(Path.cwd())
    if repo_root is None:
        return None

    stackops_root = repo_root.expanduser().resolve().joinpath(REPO_STACKOPS_DIRECTORY_NAME)
    match path_kind:
        case "prompts_yaml":
            return stackops_root / REPO_PROMPTS_YAML_FILE_NAME
        case "mcp_json":
            return stackops_root / REPO_MCP_JSON_FILE_NAME
        case "scripts":
            return stackops_root / REPO_SCRIPTS_DIRECTORY_NAME


def require_current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path:
    stackops_path = current_repo_stackops_path(path_kind=path_kind)
    if stackops_path is None:
        raise ValueError("--where repo requires running inside a git repository")
    return stackops_path
