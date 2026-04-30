from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.agents_parallel_commands import agents_create as agents_create_command
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from stackops.scripts.python.terminal import run as terminal_run_command
from stackops.utils.accessories import get_repo_root


JOB_NAME = "test_runtime"
FILE_SEPARATOR = "\n\n======== PYTHON FILE CONTEXT ========\n\n"
PROMPT_TEMPLATE = """for the following py files, please create a test under tests/runtime_tests/<file-path-relative-to-repo-root> inside the {repo_name} repository.

Use each file's repo_relative_path value to mirror the path under tests/runtime_tests/.

However, only create such file if you see there is something that must be satisfied and tested for at runtime.

I do strict type checking for static analysis and I use a dozen linters and type checkers, and that already captures everything static for me.

Please never write a test to ensure something that static analysis can already find. Only focus on things that need runtime checks.

If there is nothing to be checked at runtime, then skip the file and don't write anything.
"""


def _get_context_path(*, repo_root: Path) -> Path:
    return repo_root / ".ai" / "agents" / JOB_NAME / "context.md"


def _get_layout_path(*, repo_root: Path) -> str:
    return str(repo_root / ".ai" / "agents" / JOB_NAME / "layout.json")


def _should_exclude_path(*, relative_path: Path) -> bool:
    return any(path_part == ".venv" or path_part.startswith(".") for path_part in relative_path.parts)


def _collect_python_files(*, search_root: Path) -> list[Path]:
    python_files = [
        file_path
        for file_path in search_root.rglob("*.py")
        if file_path.is_file() and not _should_exclude_path(relative_path=file_path.relative_to(search_root))
    ]
    return sorted(python_files, key=lambda file_path: file_path.relative_to(search_root).as_posix())


def _build_context_entry(*, repo_root: Path, search_root: Path, file_path: Path) -> str:
    repo_relative_path = file_path.relative_to(repo_root).as_posix()
    scope_relative_path = file_path.relative_to(search_root).as_posix()
    source_text = file_path.read_text(encoding="utf-8")
    return f"""repo_relative_path: {repo_relative_path}
scope_relative_path: {scope_relative_path}
----- BEGIN PYTHON SOURCE -----
{source_text}
----- END PYTHON SOURCE -----"""


def _write_context_file(*, repo_root: Path, search_root: Path, context_path: Path) -> int:
    python_files = _collect_python_files(search_root=search_root)
    if len(python_files) == 0:
        raise RuntimeError("No Python files found under the current directory after excluding hidden paths and .venv.")

    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_entries = [
        _build_context_entry(repo_root=repo_root, search_root=search_root, file_path=file_path)
        for file_path in python_files
    ]
    context_path.write_text(FILE_SEPARATOR.join(context_entries), encoding="utf-8")
    return len(python_files)


def _build_prompt(*, repo_name: str) -> str:
    return PROMPT_TEMPLATE.format(repo_name=repo_name)


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
    repo_root = get_repo_root(search_root)
    if repo_root is None:
        typer.echo("💥 Could not determine the repository root. Please run this command from within a git repository.", err=True)
        raise typer.Exit(code=1)

    context_path = _get_context_path(repo_root=repo_root)
    try:
        file_count = _write_context_file(repo_root=repo_root, search_root=search_root, context_path=context_path)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Prepared runtime-test context for {file_count} Python files from {search_root}.")

    agents_create_command(
        agent=agent,
        context_path=str(context_path),
        separator=FILE_SEPARATOR,
        agent_load=agent_load,
        prompt=_build_prompt(repo_name=repo_root.name),
        job_name=JOB_NAME,
    )
    proceed = typer.confirm("Agents layout for runtime test generation created. Do you want to run it now?", default=True)
    if not proceed:
        typer.echo("Agents not launched.")
        return
    terminal_run_command(
        ctx=ctx,
        layouts_file=_get_layout_path(repo_root=repo_root),
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
