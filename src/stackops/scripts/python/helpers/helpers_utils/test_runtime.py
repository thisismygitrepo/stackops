from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.agents_parallel_commands import agents_create as agents_create_command
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from stackops.scripts.python.terminal import run as terminal_run_command
from stackops.utils.accessories import get_repo_root


JOB_NAME = "test_runtime"
FILE_SEPARATOR = "\n\n"
_WORKSPACE_REPO_MARKER = ".git"
_WORKSPACE_REPO_MINIMUM = 2
_WORKSPACE_ROOT_REQUIREMENT = "inside a git repository or from a workspace directory containing multiple git repositories"
PROMPT_TEMPLATE = """for the following py files, please create a test under <repo-name>/tests/runtime_tests/<file-path-relative-to-repo-root>.

The material contains only Python file paths relative to the current workspace root. Inspect those files directly.

For each listed path, determine the git repository that contains it, then create the test under <that-repo>/tests/runtime_tests/<file-path-relative-to-that-repo-root>.

However, only create such file if you see there is something that must be satisfied and tested for at runtime.

I do strict type checking for static analysis and I use a dozen linters and type checkers, and that already captures everything static for me.

Please never write a test to ensure something that static analysis can already find. Only focus on things that need runtime checks.

If there is nothing to be checked at runtime, then skip the file and don't write anything.
"""


@dataclass(frozen=True, slots=True)
class ContextBuildResult:
    file_count: int
    repo_count: int


def _get_context_path(*, workspace_root: Path) -> Path:
    return workspace_root / ".ai" / "agents" / JOB_NAME / "context.md"


def _get_layout_path(*, workspace_root: Path) -> str:
    return str(workspace_root / ".ai" / "agents" / JOB_NAME / "layout.json")


def _resolve_workspace_root(*, current_dir: Path) -> Path | None:
    repo_root = get_repo_root(current_dir)
    if repo_root is not None:
        return repo_root

    if not current_dir.is_dir():
        return None

    try:
        child_paths = tuple(current_dir.iterdir())
    except OSError as error:
        raise ValueError(f"Cannot inspect workspace directory: {current_dir}") from error

    nested_repo_count = 0
    for child_path in child_paths:
        if child_path.is_dir() and child_path.joinpath(_WORKSPACE_REPO_MARKER).exists():
            nested_repo_count += 1
            if nested_repo_count >= _WORKSPACE_REPO_MINIMUM:
                return current_dir
    return None


def _should_exclude_path(*, relative_path: Path) -> bool:
    return any(path_part == ".venv" or path_part.startswith(".") for path_part in relative_path.parts)


def _collect_python_files(*, search_root: Path) -> list[Path]:
    python_files = [
        file_path
        for file_path in search_root.rglob("*.py")
        if file_path.is_file() and not _should_exclude_path(relative_path=file_path.relative_to(search_root))
    ]
    return sorted(python_files, key=lambda file_path: file_path.relative_to(search_root).as_posix())


def _build_context_entry(*, workspace_root: Path, file_path: Path) -> str:
    return file_path.relative_to(workspace_root).as_posix()


def _is_repo_test_file(*, repo_root: Path, file_path: Path) -> bool:
    return file_path.relative_to(repo_root).parts[:1] == ("tests",)


def _write_context_file(*, workspace_root: Path, search_root: Path, context_path: Path) -> ContextBuildResult:
    python_files = _collect_python_files(search_root=search_root)
    if len(python_files) == 0:
        raise RuntimeError("No Python files found under the current directory after excluding hidden paths and .venv.")

    context_entries: list[str] = []
    repo_roots: set[Path] = set()
    for file_path in python_files:
        repo_root = get_repo_root(file_path)
        if repo_root is None:
            continue
        repo_root_resolved = repo_root.resolve()
        try:
            repo_root_resolved.relative_to(workspace_root)
        except ValueError:
            continue
        if _is_repo_test_file(repo_root=repo_root_resolved, file_path=file_path):
            continue
        repo_roots.add(repo_root_resolved)
        context_entries.append(_build_context_entry(workspace_root=workspace_root, file_path=file_path))
    if len(context_entries) == 0:
        raise RuntimeError("No Python files found inside git repositories under the current directory.")

    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(FILE_SEPARATOR.join(context_entries), encoding="utf-8")
    return ContextBuildResult(file_count=len(context_entries), repo_count=len(repo_roots))


def _build_prompt() -> str:
    return PROMPT_TEMPLATE


def launch_test_runtime(
    ctx: typer.Context,
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent type.")] = "codex",
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", help="Number of files per prompt.")] = 10,
    max_tabs: Annotated[
        int,
        typer.Option("--max-agents", "-m", help="Maximum agents allowed in the generated layout."),
    ] = 50,
) -> None:
    search_root = Path.cwd().resolve()
    try:
        workspace_root = _resolve_workspace_root(current_dir=search_root)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    if workspace_root is None:
        typer.echo(f"💥 Could not determine a valid workspace root. Please run this command {_WORKSPACE_ROOT_REQUIREMENT}.", err=True)
        raise typer.Exit(code=1)

    context_path = _get_context_path(workspace_root=workspace_root)
    try:
        build_result = _write_context_file(workspace_root=workspace_root, search_root=search_root, context_path=context_path)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Prepared runtime-test context for {build_result.file_count} Python files across {build_result.repo_count} repositories from {search_root}."
    )

    agents_create_command(
        agent=agent,
        context_path=str(context_path),
        separator=FILE_SEPARATOR,
        agent_load=agent_load,
        prompt=_build_prompt(),
        job_name=JOB_NAME,
    )
    proceed = typer.confirm("Agents layout for runtime test generation created. Do you want to run it now?", default=True)
    if not proceed:
        typer.echo("Agents not launched.")
        return
    terminal_run_command(
        ctx=ctx,
        layouts_file=_get_layout_path(workspace_root=workspace_root),
        max_tabs=max_tabs,
        on_conflict="restart",
    )


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🧪 <tr> Create and run the runtime-test workflow for Python files under the current directory.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    cli_app.callback(invoke_without_command=True)(launch_test_runtime)
    return cli_app
