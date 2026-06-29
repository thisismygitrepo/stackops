from pathlib import Path
import fnmatch

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_graph import (
    focus_dependency_graph,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DependencyBackend,
    DependencyCheckContext,
    DependencyGraph,
    DependencyRankDirection,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_parse import (
    parse_pyan_dot,
    parse_pydeps_json,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_runner import (
    run_backend_command,
)

DEFAULT_DEPENDENCY_EXCLUDES: tuple[str, ...] = (
    ".ai",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "tests",
)
BACKEND_EXECUTABLE_NAMES: dict[DependencyBackend, str] = {
    "pyan": "pyan3",
    "pydeps": "pydeps",
}


def resolve_dependency_check_context(target: Path) -> DependencyCheckContext:
    target_path = target.expanduser().resolve()
    if target_path.exists() is False:
        raise ValueError(f"The provided path '{target}' does not exist.")
    search_root = target_path if target_path.is_dir() else target_path.parent
    repo_root = _find_nearest_repo_root(search_root)
    return DependencyCheckContext(repo_root=repo_root, target_path=target_path)


def run_backend_dependency_graph(
    context: DependencyCheckContext,
    backend: DependencyBackend,
    rankdir: DependencyRankDirection,
    focus: tuple[str, ...],
    excludes: tuple[str, ...],
) -> DependencyGraph:
    match backend:
        case "pyan":
            return _run_pyan_dependency_graph(
                context=context,
                rankdir=rankdir,
                focus=focus,
                excludes=excludes,
            )
        case "pydeps":
            return _run_pydeps_dependency_graph(
                context=context,
                rankdir=rankdir,
                focus=focus,
                excludes=excludes,
            )


def normalize_excludes(excludes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*DEFAULT_DEPENDENCY_EXCLUDES, *excludes)))


def _find_nearest_repo_root(search_root: Path) -> Path:
    for current in (search_root, *search_root.parents):
        if current.joinpath("pyproject.toml").exists() or current.joinpath(".git").exists():
            return current
    return search_root


def _run_pyan_dependency_graph(
    context: DependencyCheckContext,
    rankdir: DependencyRankDirection,
    focus: tuple[str, ...],
    excludes: tuple[str, ...],
) -> DependencyGraph:
    source_files = _collect_python_source_files(target_path=context.target_path, repo_root=context.repo_root, excludes=excludes)
    if len(source_files) == 0:
        raise ValueError(f"No Python files found under '{context.target_path}'.")
    pyan_root = _infer_pyan_root(repo_root=context.repo_root, source_files=source_files)
    command = [
        BACKEND_EXECUTABLE_NAMES["pyan"],
        "--module-level",
        "--root",
        pyan_root.as_posix(),
        "--dot",
        "--dot-rankdir",
        rankdir,
        *[source_file.as_posix() for source_file in source_files],
    ]
    completed = run_backend_command(context=context, backend="pyan", backend_command=command)
    graph = parse_pyan_dot(dot_output=completed.stdout)
    if len(focus) == 0:
        return graph
    return focus_dependency_graph(graph=graph, focus=focus)


def _run_pydeps_dependency_graph(
    context: DependencyCheckContext,
    rankdir: DependencyRankDirection,
    focus: tuple[str, ...],
    excludes: tuple[str, ...],
) -> DependencyGraph:
    command = [
        BACKEND_EXECUTABLE_NAMES["pydeps"],
        _format_backend_target(context=context),
        "--show-deps",
        "--no-output",
        "--noshow",
        "--no-config",
        "--rankdir",
        rankdir,
    ]
    if len(focus) > 0:
        command.extend(["--only", *focus])
    if len(excludes) > 0:
        command.extend(["--exclude", *excludes])
    completed = run_backend_command(context=context, backend="pydeps", backend_command=command)
    return parse_pydeps_json(stdout=completed.stdout)


def _collect_python_source_files(target_path: Path, repo_root: Path, excludes: tuple[str, ...]) -> tuple[Path, ...]:
    candidates = (target_path,) if target_path.is_file() else tuple(target_path.rglob("*.py"))
    return tuple(
        sorted(
            path
            for path in candidates
            if path.suffix == ".py" and _is_excluded(path=path, repo_root=repo_root, excludes=excludes) is False
        )
    )


def _is_excluded(path: Path, repo_root: Path, excludes: tuple[str, ...]) -> bool:
    try:
        relative_path = path.relative_to(repo_root).as_posix()
    except ValueError:
        relative_path = path.as_posix()
    path_parts = set(path.parts)
    for pattern in excludes:
        if pattern in path_parts:
            return True
        if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(relative_path, pattern):
            return True
    return False


def _infer_pyan_root(repo_root: Path, source_files: tuple[Path, ...]) -> Path:
    src_root = repo_root / "src"
    if src_root.is_dir() and all(_path_is_relative_to(path=source_file, parent=src_root) for source_file in source_files):
        return src_root
    return repo_root


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _format_backend_target(context: DependencyCheckContext) -> str:
    try:
        return context.target_path.relative_to(context.repo_root).as_posix()
    except ValueError:
        return context.target_path.as_posix()
