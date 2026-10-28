from pathlib import Path
from typing import Final, Literal, TypeAlias

from stackops.utils.repos.constants import PROJECT_ROOT_REQUIREMENT
from stackops.utils.repos.project import resolve_project_root


REPO_STACKOPS_DIRECTORY_NAME: Final[str] = ".stackops"
REPO_STACKOPS_AGENTS_DIRECTORY_NAME: Final[str] = "agents"
REPO_PROMPTS_YAML_FILE_NAME: Final[str] = "prompts.yaml"
REPO_PARALLEL_YAML_FILE_NAME: Final[str] = "parallel.yaml"
REPO_MCP_JSON_FILE_NAME: Final[str] = "mcp.json"
REPO_SCRIPTS_DIRECTORY_NAME: Final[str] = "scripts"

RepoStackopsPathKind: TypeAlias = Literal["prompts_yaml", "parallel_yaml", "mcp_json", "scripts", "secrets_json", "layouts_json"]


def current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path | None:
    project_root = resolve_project_root(current_dir=Path.cwd())
    if project_root is None:
        return None

    stackops_root = project_root / REPO_STACKOPS_DIRECTORY_NAME
    agents_root = stackops_root / REPO_STACKOPS_AGENTS_DIRECTORY_NAME
    match path_kind:
        case "prompts_yaml":
            return agents_root / REPO_PROMPTS_YAML_FILE_NAME
        case "parallel_yaml":
            return agents_root / REPO_PARALLEL_YAML_FILE_NAME
        case "mcp_json":
            return stackops_root / REPO_MCP_JSON_FILE_NAME
        case "scripts":
            return stackops_root / REPO_SCRIPTS_DIRECTORY_NAME
        case "secrets_json":
            return stackops_root / "secrets" / "secrets.json"
        case "layouts_json":
            return stackops_root / "config" / "layout.json"


def require_current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path:
    stackops_path = current_repo_stackops_path(path_kind=path_kind)
    if stackops_path is None:
        raise ValueError(f"""--source project requires {PROJECT_ROOT_REQUIREMENT}""")
    return stackops_path
