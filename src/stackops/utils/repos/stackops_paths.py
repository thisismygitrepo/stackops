from pathlib import Path
from typing import Final, Literal, TypeAlias

from stackops.utils.accessories import get_repo_root


REPO_STACKOPS_DIRECTORY_NAME: Final[str] = ".stackops"
REPO_STACKOPS_AGENTS_DIRECTORY_NAME: Final[str] = "agents"
REPO_PROMPTS_YAML_FILE_NAME: Final[str] = "prompts.yaml"
REPO_PARALLEL_YAML_FILE_NAME: Final[str] = "parallel.yaml"
REPO_MCP_JSON_FILE_NAME: Final[str] = "mcp.json"
REPO_SCRIPTS_DIRECTORY_NAME: Final[str] = "scripts"

RepoStackopsPathKind: TypeAlias = Literal["prompts_yaml", "parallel_yaml", "mcp_json", "scripts", "secrets_json", "layouts_json"]


def current_repo_stackops_path(path_kind: RepoStackopsPathKind) -> Path | None:
    repo_root = get_repo_root(Path.cwd())
    if repo_root is None:
        return None

    stackops_root = repo_root.expanduser().resolve().joinpath(REPO_STACKOPS_DIRECTORY_NAME)
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
        raise ValueError("--source project requires running inside a git repository")
    return stackops_path


def repo_stackops_yaml_paths(*, path_kind: Literal["prompts_yaml", "parallel_yaml"]) -> list[tuple[str, Path]]:
    directory = Path.cwd().resolve()
    repo_yaml = current_repo_stackops_path(path_kind=path_kind)
    file_name = REPO_PROMPTS_YAML_FILE_NAME if path_kind == "prompts_yaml" else REPO_PARALLEL_YAML_FILE_NAME
    relative_yaml = Path(REPO_STACKOPS_DIRECTORY_NAME) / REPO_STACKOPS_AGENTS_DIRECTORY_NAME / file_name
    locations: list[tuple[str, Path]] = []
    if repo_yaml is not None and repo_yaml.exists():
        locations.append(("project", repo_yaml))

    for child_directory, directory_names, _file_names in directory.walk():
        if child_directory == directory:
            directory_names[:] = sorted(
                name for name in directory_names if not name.startswith(".") and name not in {"node_modules", "__pycache__"}
            )
        else:
            directory_names.clear()
        yaml_path = child_directory / relative_yaml
        if yaml_path == repo_yaml or not yaml_path.exists():
            continue
        location_name = (
            "project" if child_directory == directory and repo_yaml is None else f"""project:{child_directory.relative_to(directory).as_posix()}"""
        )
        locations.append((location_name, yaml_path))

    if not locations:
        locations.append(("project", repo_yaml if repo_yaml is not None else directory / relative_yaml))
    return locations
