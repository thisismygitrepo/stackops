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
WORKSPACE_SOURCE_LABEL: Final[str] = "workspace"

RepoStackopsPathKind: TypeAlias = Literal["prompts_yaml", "parallel_yaml", "mcp_json", "scripts", "secrets_json", "layout_yaml"]


def _stackops_path(*, project_root: Path, path_kind: RepoStackopsPathKind) -> Path:
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
        case "layout_yaml":
            return stackops_root / "config" / "layout.yaml"


def current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path | None:
    project_root = resolve_project_root(current_dir=Path.cwd())
    if project_root is None:
        return None
    return _stackops_path(project_root=project_root, path_kind=path_kind)


def require_current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path:
    stackops_path = current_repo_stackops_path(path_kind=path_kind)
    if stackops_path is None:
        raise ValueError(f"""--source workspace requires {PROJECT_ROOT_REQUIREMENT}""")
    return stackops_path


def current_workspace_stackops_paths(path_kind: RepoStackopsPathKind) -> tuple[tuple[str, Path], ...]:
    project_root = resolve_project_root(current_dir=Path.cwd())
    if project_root is None:
        return ()
    member_paths = tuple(
        (f"""{WORKSPACE_SOURCE_LABEL}:{member_root.name}""", member_path)
        for member_root in sorted(project_root.iterdir())
        if member_root.is_dir() and (member_path := _stackops_path(project_root=member_root, path_kind=path_kind)).exists()
    )
    return ((WORKSPACE_SOURCE_LABEL, _stackops_path(project_root=project_root, path_kind=path_kind)), *member_paths)


def require_current_workspace_stackops_paths(path_kind: RepoStackopsPathKind) -> tuple[tuple[str, Path], ...]:
    workspace_paths = current_workspace_stackops_paths(path_kind=path_kind)
    if len(workspace_paths) == 0:
        raise ValueError(f"""--source workspace requires {PROJECT_ROOT_REQUIREMENT}""")
    return workspace_paths
