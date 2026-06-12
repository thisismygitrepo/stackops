from pathlib import Path
from typing import Literal, TypeAlias

ProjectPythonVersion: TypeAlias = Literal["3.11", "3.12", "3.13", "3.14"]
TypeHintDependencyMode: TypeAlias = Literal["self-contained", "import"]
InitProjectGroupKey: TypeAlias = Literal["p", "t", "types", "l", "i", "d"]
TYPE_CHECK_EXCLUDES_ENV_VAR = "STACKOPS_TYPE_CHECK_EXCLUDES"
DEFAULT_TYPE_CHECK_EXCLUDED_DIRECTORIES: tuple[str, ...] = (
    "tests",
    ".github",
    ".codex",
    ".ai",
    ".links",
    ".venv",
)
INIT_PROJECT_GROUP_KEYS: tuple[InitProjectGroupKey, ...] = (
    "p",
    "t",
    "types",
    "l",
    "i",
    "d",
)


def normalize_init_project_groups(group: str | None) -> str | None:
    if group is None:
        return None
    group_keys = [group_key.strip() for group_key in group.split(",")]
    normalized_group_keys = [
        group_key for group_key in group_keys if group_key != ""
    ]
    invalid_group_keys = [
        group_key
        for group_key in normalized_group_keys
        if group_key not in INIT_PROJECT_GROUP_KEYS
    ]
    if len(invalid_group_keys) > 0:
        invalid_groups = ", ".join(invalid_group_keys)
        valid_groups = ", ".join(INIT_PROJECT_GROUP_KEYS)
        raise ValueError(
            f"Unknown package group(s): {invalid_groups}. Valid groups: {valid_groups}."
        )
    seen_group_keys: set[str] = set()
    unique_group_keys: list[str] = []
    for group_key in normalized_group_keys:
        if group_key in seen_group_keys:
            continue
        seen_group_keys.add(group_key)
        unique_group_keys.append(group_key)
    if len(unique_group_keys) == 0:
        return None
    return ",".join(unique_group_keys)


def normalize_init_project_libraries(libraries: str | None) -> str | None:
    if libraries is None:
        return None
    libraries_stripped = libraries.strip()
    if libraries_stripped == "":
        return None
    return libraries_stripped


def resolve_pyproject_root(path: Path) -> Path:
    path_resolved = path.expanduser().resolve()
    if path_resolved.exists() is False:
        raise ValueError(f"The provided path '{path}' does not exist.")
    search_root = path_resolved if path_resolved.is_dir() else path_resolved.parent
    for current in [search_root, *search_root.parents]:
        if current.joinpath("pyproject.toml").exists():
            return current
    raise ValueError(
        f"Could not find pyproject.toml at or above '{path_resolved}'."
    )


def resolve_type_check_excluded_directory(
    repo_root: Path, excluded_directory: str
) -> str | None:
    import os

    candidate_path = Path(excluded_directory).expanduser()
    if candidate_path.is_absolute() is False:
        candidate_path = repo_root.joinpath(candidate_path)
    candidate_path_absolute = Path(os.path.abspath(candidate_path))
    if candidate_path_absolute.is_dir() is False:
        return None
    try:
        relative_directory = candidate_path_absolute.relative_to(repo_root)
    except ValueError as error:
        raise ValueError(
            f"Excluded directory '{excluded_directory}' must be inside '{repo_root}'."
        ) from error
    if relative_directory == Path("."):
        raise ValueError("Excluded directory cannot be the repository root.")
    return relative_directory.as_posix()


def resolve_type_check_excluded_directories(
    repo_root: Path, excluded_directories: list[str] | None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if excluded_directories is None:
        return (), ()
    normalized_directories: list[str] = []
    skipped_directories: list[str] = []
    seen_directories: set[str] = set()
    for excluded_directory in excluded_directories:
        normalized_directory = resolve_type_check_excluded_directory(
            repo_root=repo_root, excluded_directory=excluded_directory
        )
        if normalized_directory is None:
            skipped_directories.append(excluded_directory)
            continue
        if normalized_directory in seen_directories:
            continue
        seen_directories.add(normalized_directory)
        normalized_directories.append(normalized_directory)
    return tuple(normalized_directories), tuple(skipped_directories)


def build_type_check_environment(
    excluded_directories: tuple[str, ...],
) -> dict[str, str]:
    import json
    import os

    environment = os.environ.copy()
    environment[TYPE_CHECK_EXCLUDES_ENV_VAR] = json.dumps(
        list(excluded_directories)
    )
    return environment
