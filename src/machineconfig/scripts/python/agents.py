"""Agents management commands - lazy loading subcommands."""

from collections.abc import Sequence
from pathlib import Path
from platform import system
import shlex
import subprocess
from tempfile import NamedTemporaryFile
from typing import Annotated, Final, Literal, cast, get_args

import typer

from machineconfig.scripts.python.agents_parallel import get_app as get_parallel_app
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import (
    ReasoningEffort,
    ReasoningShortcut,
    resolve_reasoning,
)

_ASK_REASONING_AGENTS: Final[tuple[AGENTS, ...]] = ("codex", "copilot")
_ASK_REASONING_SHORTCUTS: Final[tuple[str, ...]] = cast(tuple[str, ...], get_args(ReasoningShortcut))
_ASK_REASONING_HELP: Final[str] = "n=none, l=low, m=medium, h=high, x=xhigh; supported for codex and copilot"


def _join_prompt_parts(prompt_parts: Sequence[str]) -> str:
    prompt_text = " ".join(prompt_parts).strip()
    if prompt_text == "":
        raise typer.BadParameter("""prompt must not be empty""")
    return prompt_text


def _resolve_prompt_path(prompt_parts: Sequence[str]) -> Path:
    prompt_path = Path(_join_prompt_parts(prompt_parts=prompt_parts)).expanduser()
    if not prompt_path.is_file():
        raise typer.BadParameter(f"""prompt file does not exist: {prompt_path}""")
    return prompt_path


def _build_exec_prefix(reasoning_effort: ReasoningEffort) -> list[str]:
    return [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
    ]


def build_prompt_command(reasoning_effort: ReasoningEffort, prompt: str) -> list[str]:
    return [*_build_exec_prefix(reasoning_effort=reasoning_effort), prompt]


def build_file_prompt_command(reasoning_effort: ReasoningEffort) -> list[str]:
    return [*_build_exec_prefix(reasoning_effort=reasoning_effort), "-"]


def _quote_for_shell(value: str, *, is_windows: bool) -> str:
    if is_windows:
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def _build_copilot_ask_command(prompt_file: Path, reasoning_effort: ReasoningEffort | None) -> str:
    is_windows = system() == "Windows"
    prompt_file_q = _quote_for_shell(str(prompt_file), is_windows=is_windows)
    if is_windows:
        prompt_content_expr = f"(Get-Content -Raw {prompt_file_q})"
    else:
        prompt_content_expr = f'"$(cat {prompt_file_q})"'
    reasoning_arg = ""
    if reasoning_effort is not None:
        reasoning_arg = f" --reasoning-effort {reasoning_effort}"
    return f"copilot{reasoning_arg} -p {prompt_content_expr} --yolo"


def build_ask_command(agent: AGENTS, prompt_file: Path, reasoning_effort: ReasoningEffort | None) -> str:
    if reasoning_effort is not None and agent not in _ASK_REASONING_AGENTS:
        raise ValueError("--reasoning is only supported for --agent codex or --agent copilot")
    if agent == "copilot":
        return _build_copilot_ask_command(prompt_file=prompt_file, reasoning_effort=reasoning_effort)
    return build_agent_command(agent=agent, prompt_file=prompt_file, reasoning_effort=reasoning_effort)


def _run_subprocess(command: Sequence[str], stdin_text: str | None) -> int:
    try:
        completed_process = subprocess.run(command, check=False, input=stdin_text, text=stdin_text is not None)
    except FileNotFoundError as error:
        filename = error.filename or command[0]
        strerror = error.strerror or "unknown error"
        typer.echo(f"""Failed to execute {filename!r}: {strerror}""", err=True)
        return 1
    return completed_process.returncode


def run_command(command: Sequence[str]) -> int:
    return _run_subprocess(command=command, stdin_text=None)


def run_shell_command(command_line: str) -> int:
    if system() == "Windows":
        return _run_subprocess(command=["powershell", "-NoProfile", "-Command", command_line], stdin_text=None)
    return _run_subprocess(command=["bash", "-lc", command_line], stdin_text=None)


def run_command_with_prompt_file(command: Sequence[str], prompt_path: Path) -> int:
    try:
        return _run_subprocess(command=command, stdin_text=prompt_path.read_text(encoding="utf-8"))
    except OSError as error:
        strerror = error.strerror or "unknown error"
        typer.echo(f"""Failed to read prompt file {str(prompt_path)!r}: {strerror}""", err=True)
        return 1


def _write_temporary_prompt_file(prompt_text: str) -> Path:
    with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", prefix="agents_ask_", delete=False) as prompt_file:
        prompt_file.write(prompt_text)
        return Path(prompt_file.name)


def _split_legacy_ask_reasoning(agent: AGENTS, reasoning: ReasoningShortcut | None, prompt_parts: Sequence[str]) -> tuple[ReasoningShortcut | None, list[str]]:
    normalized_prompt_parts = list(prompt_parts)
    if reasoning is not None:
        return reasoning, normalized_prompt_parts
    if agent not in _ASK_REASONING_AGENTS:
        return None, normalized_prompt_parts
    if len(normalized_prompt_parts) <= 1:
        return None, normalized_prompt_parts
    first_prompt_part = normalized_prompt_parts[0]
    if first_prompt_part not in _ASK_REASONING_SHORTCUTS:
        return None, normalized_prompt_parts
    return cast(ReasoningShortcut, first_prompt_part), normalized_prompt_parts[1:]


def _resolve_ask_reasoning(agent: AGENTS, reasoning: ReasoningShortcut | None) -> ReasoningEffort | None:
    if reasoning is None:
        return None
    if agent not in _ASK_REASONING_AGENTS:
        raise typer.BadParameter("--reasoning is only supported for --agent codex or --agent copilot")
    try:
        return resolve_reasoning(shortcut=reasoning, agent=agent)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


def init_config(
    root: Annotated[
        str, typer.Option(..., "--root", "-r", help="Root directory of the repository to initialize AI configs in. Defaults to current directory.")
    ],
    agents: Annotated[
        str, typer.Option("--agent", "-a", help=f"AI agents to configure (comma-separated), default is all of them. {','.join(get_args(AGENTS))}")
    ] = "",
    add_config: Annotated[bool, typer.Option("--add-config", "-c", help="Create private agent config files/directories")] = True,
    add_instructions: Annotated[bool, typer.Option("--add-instructions", "-i", help="Create agent instructions files (e.g. AGENTS.md)")] = True,
    add_scripts: Annotated[bool, typer.Option("--include-scripts", "-s", help="Create shared .ai/.scripts scaffold")] = False,
    add_vscode_tasks: Annotated[bool, typer.Option("--add-vscode-tasks", "-l", help="Add VS Code lint/type-check task only")] = False,
    add_to_gitignore: Annotated[
        bool, typer.Option("--add-gitignore", "-g", help="Track all files touched by init-config and add them to .gitignore")
    ] = False,
) -> None:
    """Initialize AI configurations in the current repository."""
    from machineconfig.scripts.python.helpers.helpers_agents.agents_impl import init_config as impl

    try:
        from typing import cast

        if agents:
            frameworks__ = tuple(agent.strip() for agent in agents.split(",") if agent.strip())
            resolved: tuple[AGENTS, ...] = cast(tuple[AGENTS, ...], frameworks__)
        else:
            resolved = cast(tuple[AGENTS, ...], get_args(AGENTS))

        impl(
            root=root,
            frameworks=resolved,
            include_common=add_scripts,
            add_all_configs_to_gitignore=add_to_gitignore,
            add_lint_task=add_vscode_tasks,
            add_config=add_config,
            add_instructions=add_instructions,
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def make_todo_files(
    pattern: Annotated[str, typer.Argument(help="Pattern or keyword to match files by")] = ".py",
    repo: Annotated[str, typer.Argument(help="Repository path. Can be any directory within a git repository.")] = ".",
    strategy: Annotated[
        Literal["name", "keywords"],
        typer.Option("-s", "--strategy", help="Strategy to filter files: 'name' for filename matching, 'keywords' for content matching"),
    ] = "name",
    exclude_init: Annotated[bool, typer.Option("-x", "--exclude-init", help="Exclude __init__.py files from the checklist")] = True,
    include_line_count: Annotated[bool, typer.Option("-l", "--line-count", help="Include line count column in the output")] = False,
    output_path: Annotated[str, typer.Option("-o", "--output-path", help="Base path for output files relative to repo root")] = ".ai/todo/files",
    format_type: Annotated[Literal["csv", "md", "txt"], typer.Option("-f", "--format", help="Output format: csv, md (markdown), or txt")] = "md",
    split_every: Annotated[
        int | None, typer.Option("--split-every", "-e", help="Split output into multiple files, each containing at most this many results")
    ] = None,
    split_to: Annotated[int | None, typer.Option("--split-to", "-t", help="Split output into exactly this many files")] = None,
) -> None:
    """Generate checklist with Python and shell script files in the repository filtered by pattern."""
    from machineconfig.scripts.python.ai.utils.generate_files import make_todo_files as impl

    impl(
        pattern=pattern,
        repo=repo,
        strategy=strategy,
        exclude_init=exclude_init,
        include_line_count=include_line_count,
        output_path=output_path,
        format_type=format_type,
        split_every=split_every,
        split_to=split_to,
    )


def create_symlink_command(num: Annotated[int, typer.Argument(help="Number of symlinks to create (1-5).")] = 5) -> None:
    """Create symlinks to repo_root at ~/code_copies/${repo_name}_copy_{i}."""
    from machineconfig.scripts.python.ai.utils.generate_files import create_symlink_command as impl

    impl(num=num)


def run_prompt(
    prompt: Annotated[str | None, typer.Argument(help="Prompt text (optional positional argument). If omitted, an empty prompt is used.")] = None,
    agent: Annotated[AGENTS, typer.Option(..., "--agent", "-a", help="Agent to launch.")] = "copilot",
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(..., "--reasoning-effort", "-r", help="Reasoning effort for codex agents. When omitted, codex uses its default."),
    ] = None,
    context: Annotated[str | None, typer.Option(..., "--context", "-c", help="Context string. Mutually exclusive with --context-path.")] = None,
    context_path: Annotated[
        str | None, typer.Option(..., "--context-path", "-C", help="Path to a context file. Mutually exclusive with --context.")
    ] = None,
    context_yaml_path: Annotated[
        str | None,
        typer.Option(
            ...,
            "--context-yaml-path",
            "-y",
            help="YAML file used for interactive context selection fallback. Auto-created with commented template if missing.",
        ),
    ] = None,
    context_name: Annotated[
        str | None,
        typer.Option(
            ...,
            "--context-name",
            "-n",
            help="YAML section key (supports dot-path, e.g. 'team.backend'). Used with --context-yaml-path or default context YAML.",
        ),
    ] = None,
    where: Annotated[
        Literal["all", "a", "private", "p", "public", "b", "library", "l", "custom", "c"],
        typer.Option(..., "--where", "-w", help="Where to look for context YAML files when --context-yaml-path is not provided."),
    ] = "all",
    show_prompts_yaml_format: Annotated[
        bool,
        typer.Option(
            ...,
            "--show-format",
            "-Y",
            help="Show prompts YAML format guidance and resolved file path. If no prompt/context input is provided, exits after showing it.",
        ),
    ] = False,
    edit: Annotated[
        bool,
        typer.Option(
            ...,
            "--edit",
            "-e",
            help="Open prompts YAML in an editor (hx preferred, nano fallback). If no prompt/context input is provided, exits after editing.",
        ),
    ] = False,
) -> None:
    """Run one prompt via selected agent."""
    from machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl import run as impl

    try:
        impl(
            prompt=prompt,
            agent=agent,
            reasoning_effort=reasoning_effort,
            context=context,
            context_path=context_path,
            prompts_yaml_path=context_yaml_path,
            context_name=context_name,
            where=where,
            edit=edit,
            show_prompts_yaml_format=show_prompts_yaml_format,
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def ask(
    prompt: Annotated[
        list[str],
        typer.Argument(help="Prompt text to pass to the selected agent, or a prompt file path when --file-prompt is set"),
    ],
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent to ask directly.")] = "codex",
    reasoning: Annotated[
        ReasoningShortcut | None,
        typer.Option("--reasoning", "-r", help=_ASK_REASONING_HELP),
    ] = None,
    file_prompt: Annotated[
        bool,
        typer.Option("--file-prompt", "-f", help="Treat PROMPT as a file path and pass its contents to the selected agent"),
    ] = False,
) -> None:
    """Ask a selected agent directly."""
    reasoning_shortcut, prompt_parts = _split_legacy_ask_reasoning(agent=agent, reasoning=reasoning, prompt_parts=prompt)
    reasoning_effort = _resolve_ask_reasoning(agent=agent, reasoning=reasoning_shortcut)
    if file_prompt:
        prompt_path = _resolve_prompt_path(prompt_parts=prompt_parts)
        try:
            return_code = run_shell_command(command_line=build_ask_command(agent=agent, prompt_file=prompt_path, reasoning_effort=reasoning_effort))
        except ValueError as error:
            raise typer.BadParameter(str(error)) from error
        raise typer.Exit(code=return_code)

    prompt_text = _join_prompt_parts(prompt_parts=prompt_parts)
    prompt_path = _write_temporary_prompt_file(prompt_text=prompt_text)
    try:
        try:
            return_code = run_shell_command(command_line=build_ask_command(agent=agent, prompt_file=prompt_path, reasoning_effort=reasoning_effort))
        except ValueError as error:
            raise typer.BadParameter(str(error)) from error
    finally:
        prompt_path.unlink(missing_ok=True)
    raise typer.Exit(code=return_code)


def add_skill(
    skill_name: Annotated[str, typer.Argument(help="Name of the skill to add.")],
    _agent: Annotated[AGENTS, typer.Option(..., "--agent", "-a", help="Agent to add the skill to.")] = "copilot",
    directory: Annotated[
        str | None,
        typer.Option(..., "--directory", "-d", help="Directory to add the skill to. If not provided, defaults to current working directory."),
    ] = None,
) -> None:
    """Add a skill to an agent in a directory."""
    opensource_skills = {"agent-browser": "bunx skills add vercel-labs/agent-browser"}
    if directory:
        agent_dir = Path(directory).expanduser().resolve()
        if not agent_dir.is_dir():
            typer.echo(f"Provided directory '{directory}' does not exist or is not a directory.")
            raise typer.Exit(1)
    else:
        agent_dir = Path.cwd()
    if skill_name in opensource_skills:
        from machineconfig.utils.code import exit_then_run_shell_script

        command = opensource_skills[skill_name]
        command = f"""
cd {agent_dir}
{command}
"""
        exit_then_run_shell_script(command, strict=False)
    else:
        typer.echo(f"Skill '{skill_name}' is not recognized. Please provide a valid skill name.")


def get_app() -> typer.Typer:
    agents_app = typer.Typer(help="🤖 AI Agents management subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    agents_app.add_typer(
        get_parallel_app(),
        name="parallel",
        help="🧵 <p> Parallel agent workflow commands",
        short_help="<p> Parallel agent workflow commands",
    )
    agents_app.add_typer(get_parallel_app(), name="p", help="Parallel agent workflow commands", hidden=True)
    agents_app.command(
        "make-config", no_args_is_help=True, help=init_config.__doc__, short_help="<g> Initialize AI configurations in the current repository"
    )(init_config)
    agents_app.command("g", no_args_is_help=True, help=init_config.__doc__, hidden=True)(init_config)
    agents_app.command("make-todo", no_args_is_help=True, short_help="<d> Generate a markdown file listing all Python files in the repo")(
        make_todo_files
    )
    agents_app.command("d", no_args_is_help=True, hidden=True)(make_todo_files)
    agents_app.command(name="make-symlinks", no_args_is_help=True, short_help="<l> Create symlinks to the current repo in ~/code_copies/")(
        create_symlink_command
    )
    agents_app.command(name="l", no_args_is_help=True, hidden=True)(create_symlink_command)
    agents_app.command(name="run-prompt", no_args_is_help=True, short_help="<r> Run one prompt via selected agent")(run_prompt)
    agents_app.command(name="r", no_args_is_help=True, hidden=True)(run_prompt)
    agents_app.command(name="ask", no_args_is_help=True, short_help="<a> Ask a selected agent directly")(ask)
    agents_app.command(name="a", no_args_is_help=True, hidden=True)(ask)
    agents_app.command(name="add-skill", no_args_is_help=True, short_help="<s> Add a skill to an agent")(add_skill)
    agents_app.command(name="s", no_args_is_help=True, hidden=True)(add_skill)
    return agents_app


def main() -> None:
    agents_app = get_app()
    agents_app()


if __name__ == "__main__":
    main()
