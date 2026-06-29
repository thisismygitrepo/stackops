"""Agents management commands - lazy loading subcommands."""

from pathlib import Path
import shutil
from typing import Annotated, Final, Literal, TypeAlias, cast, get_args

import typer

from stackops.scripts.python.helpers.helpers_agents.mcp_types import MCP_CATALOG_SOURCE
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort, ReasoningShortcut
from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, DEFAULT_AGENT

_MCP_INSTALL_SCOPE: TypeAlias = Literal["local", "global"]
_PROMPTS_SOURCE: TypeAlias = Literal["all", "a", "repo", "r", "private", "p", "public", "b", "library", "l"]
_SKILL_INSTALL_SCOPE: TypeAlias = Literal["local", "global"]
_SKILL_INSTALL_BACKEND: TypeAlias = Literal["bunx", "npx", "stackops", "s"]
_HEADROOM_AGENT: TypeAlias = Literal["codex", "copilot"]

_ASK_REASONING_HELP: Final[str] = "n=none, l=low, m=medium, h=high, x=xhigh; supported for codex, copilot, and pi"
_AGENT_VALUES: Final[tuple[AGENTS, ...]] = cast(tuple[AGENTS, ...], get_args(AGENTS))
_INIT_CONFIG_ALL_AGENTS: Final[str] = "all"
INTERACTIVE_AGENT: TypeAlias = Literal["codex", "x", "copilot", "c", "pi", "p", "opencode", "omp", "o"]
_CAVEMAN_INITIAL_PROMPT: Final[str] = "Use $caveman wenyan-full for this entire session."
_HEADROOM_COMMAND: Final[str] = "headroom"
_HEADROOM_AGENTS: Final[tuple[_HEADROOM_AGENT, ...]] = ("codex", "copilot")
_INTERACTIVE_AGENT_ALIASES: Final[dict[INTERACTIVE_AGENT, AGENTS]] = {
    "codex": "codex",
    "x": "codex",
    "copilot": "copilot",
    "c": "copilot",
    "pi": "pi",
    "p": "pi",
    "opencode": "opencode",
    "omp": "opencode",
    "o": "opencode",
}
_INIT_CONFIG_AGENT_HELP: Final[str] = (
    f"AI agents to configure (comma-separated). Pass '{_INIT_CONFIG_ALL_AGENTS}' to configure all of them. "
    f"{','.join(_AGENT_VALUES)}"
)


def _parse_init_config_agents(*, raw_value: str) -> tuple[AGENTS, ...]:
    parts = [part.strip() for part in raw_value.split(",")]
    if any(part == "" for part in parts):
        raise ValueError("Agent names must be a comma-separated list without empty entries")
    if _INIT_CONFIG_ALL_AGENTS in parts:
        if len(parts) != 1:
            raise ValueError("Do not mix 'all' with specific agent names")
        return _AGENT_VALUES

    resolved_agents: list[AGENTS] = []
    seen_agents: set[str] = set()
    for part in parts:
        if part not in _AGENT_VALUES:
            raise ValueError(f"Unsupported agent: {part}. Supported agents: all, {', '.join(_AGENT_VALUES)}")
        if part in seen_agents:
            continue
        seen_agents.add(part)
        resolved_agents.append(part)
    return tuple(resolved_agents)


def init_config(
    agents: Annotated[
        str, typer.Option(..., "--agent", "-a", help=_INIT_CONFIG_AGENT_HELP)
    ],
    root: Annotated[
        str | None,
        typer.Option("--root", "-r", help="Root directory of the repository to initialize AI configs in. Defaults to current directory."),
    ] = None,
    add_config: Annotated[
        bool,
        typer.Option("--no-add-config", "-C", help="Skip private agent config files/directories"),
    ] = True,
    add_instructions: Annotated[
        bool,
        typer.Option("--no-add-instructions", "-I", help="Skip agent instruction files (e.g. AGENTS.md)"),
    ] = True,
    add_scripts: Annotated[bool, typer.Option("--include-scripts", "-s", help="Create shared .ai and scripts/type_checking scaffold")] = False,
    add_vscode_tasks: Annotated[bool, typer.Option("--add-vscode-tasks", "-l", help="Add VS Code lint/type-check task only")] = False,
    add_to_gitignore: Annotated[
        bool, typer.Option("--add-gitignore", "-g", help="Track all files touched by init-config and add them to .gitignore")
    ] = False,
) -> None:
    """Initialize AI configurations in the current repository."""
    from stackops.scripts.python.helpers.helpers_agents.agents_impl import init_config as impl

    try:
        resolved = _parse_init_config_agents(raw_value=agents)

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


def add_mcp(
    requested_mcp_servers: Annotated[
        str | None, typer.Argument(help="MCP server names or supported agent skills to resolve from stackops catalogs (comma-separated).")
    ] = None,
    agents: Annotated[
        str, typer.Option("--agent", "-a", help=f"AI agents to configure (comma-separated), default is all of them. {','.join(get_args(AGENTS))}")
    ] = "",
    scope: Annotated[
        _MCP_INSTALL_SCOPE, typer.Option("--scope", "-s", help="Install MCP config or skill files into repo-local or user-global agent config.")
    ] = "local",
    source: Annotated[MCP_CATALOG_SOURCE, typer.Option(..., "--source", "-S", help="Source to resolve or edit MCP catalog files.")] = "all",
    edit: Annotated[
        bool,
        typer.Option(
            ...,
            "--edit",
            "-e",
            help="Open MCP catalog files in an editor (hx preferred, nano fallback). If no MCP names are provided, exits after editing.",
        ),
    ] = False,
) -> None:
    """Resolve MCP servers from stackops catalogs, install supported agent skills, or edit catalogs."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_mcp_impl import add_mcp as impl

        impl(requested_mcp_servers=requested_mcp_servers, agents=agents, scope=scope, source=source, edit=edit, report=typer.echo)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def _resolve_interactive_agent(agent: INTERACTIVE_AGENT) -> AGENTS:
    return _INTERACTIVE_AGENT_ALIASES[agent]


def _interactive_agent_command(agent: AGENTS, caveman: bool) -> list[str]:
    match agent:
        case "codex":
            command = ["codex", "--dangerously-bypass-approvals-and-sandbox"]
            if caveman:
                command.append(_CAVEMAN_INITIAL_PROMPT)
            return command
        case "copilot":
            command = ["copilot", "--yolo"]
            if caveman:
                command.extend(["--interactive", _CAVEMAN_INITIAL_PROMPT])
            return command
        case "pi":
            command = ["pi"]
            if caveman:
                command.append(_CAVEMAN_INITIAL_PROMPT)
            return command
        case "opencode":
            command = ["omp"]
            if caveman:
                command.append(_CAVEMAN_INITIAL_PROMPT)
            return command
        case _:
            raise ValueError(f"Unsupported interactive agent: {agent}")


def _apply_headroom(command: list[str], agent: AGENTS, headroom: bool) -> list[str]:
    if headroom:
        resolved_headroom = shutil.which(_HEADROOM_COMMAND)
        if resolved_headroom is None:
            raise ValueError("Required command not found: headroom. Install headroom or run without --headroom.")
        if agent not in _HEADROOM_AGENTS:
            supported_agents = ", ".join(_HEADROOM_AGENTS)
            raise ValueError(f"headroom does not support {agent}. Supported agents: {supported_agents}.")
        passthrough_args = command[1:]
        return [resolved_headroom, "wrap", agent, "--", *passthrough_args]
    return command


def run_interactive(
    agent: Annotated[
        INTERACTIVE_AGENT,
        typer.Option(..., "--agent", "-a", help="Agent to launch: codex/x, copilot/c, pi/p, or omp/o."),
    ] = cast(INTERACTIVE_AGENT, DEFAULT_AGENT),
    caveman: Annotated[
        bool,
        typer.Option(..., "--caveman", "-c", help="Start the session with the caveman wenyan-full prompt."),
    ] = False,
    headroom: Annotated[
        bool,
        typer.Option(..., "--headroom", "-h", help="Launch the session through headroom."),
    ] = False,
) -> None:
    """Launch an agent with reasonable defaults."""
    import shlex

    resolved_agent = _resolve_interactive_agent(agent=agent)
    try:
        command = _apply_headroom(
            command=_interactive_agent_command(agent=resolved_agent, caveman=caveman), agent=resolved_agent, headroom=headroom
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(script=shlex.join(command), strict=False)


def run_prompt(
    prompt: Annotated[
        list[str],
        typer.Argument(
            default_factory=list,
            help="Prompt text. Use -- before the prompt to pass option-looking text as prompt content.",
        ),
    ],
    agent: Annotated[AGENTS, typer.Option(..., "--agent", "-a", help="Agent to launch.")] = DEFAULT_AGENT,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(
            ...,
            "--reasoning",
            "-r",
            help="Reasoning effort for codex, copilot, and pi agents. Unsupported agents ignore it and use their default.",
        ),
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
    source: Annotated[
        _PROMPTS_SOURCE,
        typer.Option(..., "--source", "-s", help="Source to look for context YAML files when --context-yaml-path is not provided."),
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
    from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import run as impl

    try:
        impl(
            prompt=" ".join(prompt) if prompt else None,
            agent=agent,
            reasoning_effort=reasoning_effort,
            context=context,
            context_path=context_path,
            prompts_yaml_path=context_yaml_path,
            context_name=context_name,
            source=source,
            edit=edit,
            show_prompts_yaml_format=show_prompts_yaml_format,
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def ask(
    prompt: Annotated[list[str], typer.Argument(help="Prompt text to pass to the selected agent.")],
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent to ask directly.")] = DEFAULT_AGENT,
    reasoning: Annotated[ReasoningShortcut | None, typer.Option("--reasoning", "-r", help=_ASK_REASONING_HELP)] = None,
    file_prompt: Annotated[
        Path | None, typer.Option("--file-prompt", "-f", help="Append the contents of this file to PROMPT before asking the selected agent.")
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Skip the Rich preflight summary and stream agent output directly.")] = False,
) -> None:
    """Ask a selected agent directly."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_ask_impl import run_ask as impl

        return_code = impl(prompt_parts=prompt, agent=agent, reasoning=reasoning, file_prompt=file_prompt, quiet=quiet)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    raise typer.Exit(code=return_code)


def plan(
    prompt: Annotated[
        list[str],
        typer.Argument(
            help="Plan objective. Use -- before the objective to pass option-looking text as prompt content.",
        ),
    ],
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent to generate the plan.")] = DEFAULT_AGENT,
) -> None:
    """Generate an agentops plan JSON file via selected agent."""
    from stackops.scripts.python.helpers.helpers_agents.agents_plan_impl import run_plan as impl

    try:
        plan_path = impl(user_prompt=" ".join(prompt), agent=agent)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"Plan target: {plan_path}")


def execute(
    plan_json: Annotated[
        Path | None,
        typer.Argument(help="Plan JSON file generated by `agents plan`. If omitted, execute the only .ai/plans/*.plan.json file."),
    ] = None,
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent used to check whether the active phase is finished.")] = DEFAULT_AGENT,
    interval_seconds: Annotated[int, typer.Option("--interval", "-i", help="Seconds to sleep between executor passes.")] = 300,
    once: Annotated[bool, typer.Option("--once", help="Run one executor pass and exit.")] = False,
) -> None:
    """Execute an agentops plan JSON file."""
    import typer as _typer

    from stackops.scripts.python.helpers.helpers_agents.agents_execute_impl import run_execute as impl

    try:
        impl(plan_path=plan_json, checker_agent=agent, interval_seconds=interval_seconds, once=once, report=_typer.echo)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


def add_skill(
    skill_name: Annotated[
        str | None, typer.Argument(help="Name(s) of the skills to add, comma-separated. If omitted, opens an interactive multi-select picker.")
    ] = None,
    agent: Annotated[
        str | None,
        typer.Option(
            ...,
            "--agent",
            "-a",
            help="Optional upstream skills CLI agent target, passed through without StackOps mapping. Comma-separated values are accepted.",
        ),
    ] = None,
    scope: Annotated[
        _SKILL_INSTALL_SCOPE, typer.Option("--scope", "-s", help="Install the skill into the repo-local or user-global agent skill directory.")
    ] = "local",
    directory: Annotated[
        str | None,
        typer.Option(..., "--directory", "-d", help="Directory to add the skill to. If not provided, defaults to current working directory."),
    ] = None,
    backend: Annotated[
        _SKILL_INSTALL_BACKEND,
        typer.Option("--backend", "-b", help="Install backend: bunx/npx use the upstream skills CLI; stackops/s copies bundled skills locally."),
    ] = "stackops",
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Pass --yes to the upstream skills CLI."),
    ] = False,
) -> None:
    """Add a skill through an installer backend."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import add_skill as impl

        return_code = impl(skill_name=skill_name, agent=agent, scope=scope, directory=directory, backend=backend, yes=yes)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    raise typer.Exit(code=return_code)


def get_app() -> typer.Typer:
    from stackops.scripts.python.agents_browser import get_app as get_browser_app
    from stackops.scripts.python.agents_iter import get_app as get_iter_app
    from stackops.scripts.python.agents_parallel import get_app as get_parallel_app

    agents_app = typer.Typer(help="🤖 AI Agents management subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    agents_app.add_typer(
        get_parallel_app(), name="parallel", help="🧵 <p> Parallel agent workflow commands", short_help="<p> Parallel agent workflow commands"
    )
    agents_app.add_typer(get_parallel_app(), name="p", help="Parallel agent workflow commands", hidden=True)
    agents_app.add_typer(
        get_browser_app(), name="browser", help="🌐 <b> Browser automation for agent CLIs and MCP", short_help="<b> Browser automation for agent CLIs/MCP"
    )
    agents_app.add_typer(get_browser_app(), name="b", help="Browser automation for agent CLIs and MCP", hidden=True)
    agents_app.add_typer(get_iter_app(), name="iter", help="🔁 <I> Iter workflow maintenance commands", short_help="<I> Iter workflow maintenance")
    agents_app.add_typer(get_iter_app(), name="I", help="Iter workflow maintenance commands", hidden=True)

    agents_app.command(name="add-mcp", short_help="<m> Resolve catalog MCP entries or supported skills")(add_mcp)
    agents_app.command(name="m", hidden=True)(add_mcp)
    agents_app.command(name="add-skill", short_help="<s> Add a skill to an agent")(add_skill)
    agents_app.command(name="s", hidden=True)(add_skill)
    agents_app.command(
        "add-config", no_args_is_help=True, help=init_config.__doc__, short_help="<c> Initialize AI configurations in the current repository"
    )(init_config)
    agents_app.command("c", no_args_is_help=True, help=init_config.__doc__, hidden=True)(init_config)

    agents_app.command(name="run-prompt", no_args_is_help=False, short_help="<r> Run one prompt via selected agent")(run_prompt)
    agents_app.command(name="r", no_args_is_help=False, hidden=True)(run_prompt)
    agents_app.command(name="run-interactive", no_args_is_help=False, short_help="<i> Launch an agent with reasonable defaults")(
        run_interactive
    )
    agents_app.command(name="i", no_args_is_help=False, hidden=True)(run_interactive)
    agents_app.command(name="ask", no_args_is_help=True, short_help="<a> Ask a selected agent directly")(ask)
    agents_app.command(name="a", no_args_is_help=True, hidden=True)(ask)
    agents_app.command(name="plan", no_args_is_help=True, short_help="<P> Generate an agentops plan JSON via selected agent")(plan)
    agents_app.command(name="P", no_args_is_help=True, hidden=True)(plan)
    agents_app.command(name="execute", no_args_is_help=False, short_help="<E> Execute an agentops plan JSON")(execute)
    agents_app.command(name="E", no_args_is_help=False, hidden=True)(execute)
    return apply_alias_markers(agents_app)


def main() -> None:
    agents_app = get_app()
    agents_app()


if __name__ == "__main__":
    main()
