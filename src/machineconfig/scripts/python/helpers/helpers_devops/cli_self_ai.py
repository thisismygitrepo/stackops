from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from machineconfig.scripts.python.helpers.helpers_agents.agents_impl import agents_create as agents_create_impl
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


DEFAULT_JOB_NAME = "updateInstallerData"
DEFAULT_SEPARATOR = "    },\n    {"
UPDATE_INSTALLER_PROMPT = """for each of the bellow, please check if its github repo, then, do the following
make sure that file name patter are up to date and as per the release page

modify the target file directly @ /home/alex/code/machineconfig/src/machineconfig/jobs/installer/installer_data.json
but please only wokr on entries designated for you, ignore the rest because the file is too big, other agents are working on it now.

Notes:
* File pattern should  never be ..v{version}.. with v, even if they have that in release page, the v is implicit.
* If file pattern is "<name>.py" then it is referencing a custom py script installer, in which case, please don't touch it, at all, no matter what.
* If file pattern is a custom package installtion command, please don't touch it.
* don't touch any other field other than thee file pattern.
"""


@dataclass(frozen=True)
class UpdateInstallerDefaults:
    repo_root: Path
    context_path: Path
    agents_dir: Path
    output_path: Path


def get_developer_repo_root() -> Path:
    return Path.home().joinpath("code", "machineconfig")


def get_update_installer_defaults(*, job_name: str) -> UpdateInstallerDefaults:
    repo_root = get_developer_repo_root()
    agents_dir = repo_root.joinpath(".ai", "agents", job_name)
    return UpdateInstallerDefaults(
        repo_root=repo_root,
        context_path=repo_root.joinpath("src", "machineconfig", "jobs", "installer", "installer_data.json"),
        agents_dir=agents_dir,
        output_path=agents_dir.joinpath("layout.json"),
    )


def _resolve_context_path(*, context: str | None, context_path: str | None, defaults: UpdateInstallerDefaults) -> str | None:
    if context is not None:
        return None
    if context_path is not None:
        return context_path
    return str(defaults.context_path)


def _resolve_prompt(
    *,
    prompt: str | None,
    prompt_path: str | None,
    prompt_name: str | None,
    defaults: UpdateInstallerDefaults,
) -> str | None:
    _ = defaults
    if prompt is not None:
        return prompt
    if prompt_path is not None or prompt_name is not None:
        return None
    return UPDATE_INSTALLER_PROMPT


def _resolve_prompt_path(
    *,
    prompt: str | None,
    prompt_path: str | None,
    prompt_name: str | None,
) -> str | None:
    if prompt is not None or prompt_name is not None:
        return None
    if prompt_path is not None:
        return prompt_path
    return None


def _resolve_agents_dir(*, agents_dir: str | None, defaults: UpdateInstallerDefaults) -> str:
    if agents_dir is not None:
        return agents_dir
    return str(defaults.agents_dir)


def _resolve_output_path(*, output_path: str | None, resolved_agents_dir: str, defaults: UpdateInstallerDefaults) -> str:
    if output_path is not None:
        return output_path
    if resolved_agents_dir != str(defaults.agents_dir):
        return str(Path(resolved_agents_dir).joinpath("layout.json"))
    return str(defaults.output_path)


def update_installer(
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent type.")] = "codex",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use, agent will use its default otherwise.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option("--reasoning-effort", "-r", help="Reasoning effort for codex agents. When omitted, codex uses its default."),
    ] = None,
    provider: Annotated[PROVIDER | None, typer.Option("--provider", "-v", help="Provider to use (if the agent supports many).")] = None,
    host: Annotated[HOST, typer.Option("--host", "-h", help="Machine to run agents on.")] = "local",
    context: Annotated[
        str | None,
        typer.Option("--context", "-c", help="Context as a direct string. Mutually exclusive with --context-path."),
    ] = None,
    context_path: Annotated[
        str | None,
        typer.Option(
            "--context-path",
            "-C",
            help="Context file or folder path. Defaults to src/machineconfig/jobs/installer/installer_data.json when --context is omitted.",
        ),
    ] = None,
    separator: Annotated[
        str,
        typer.Option("--separator", "-s", help="Separator for context. Supports escaped values like '\\n'."),
    ] = DEFAULT_SEPARATOR,
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", help="Number of tasks per prompt.")] = 10,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Prompt prefix as string.")] = None,
    prompt_path: Annotated[
        str | None,
        typer.Option(
            "--prompt-path",
            "-P",
            help="Prompt file path. When omitted, update-installer uses its embedded default prompt unless --prompt or --prompt-name is provided.",
        ),
    ] = None,
    prompt_name: Annotated[str | None, typer.Option("--prompt-name", "-N", help="Prompt entry name from prompts YAML.")] = None,
    job_name: Annotated[str, typer.Option("--job-name", "-n", help="Job label and default output directory stem.")] = DEFAULT_JOB_NAME,
    join_prompt_and_context: Annotated[
        bool,
        typer.Option("--joined-prompt-context", "-j", help="Join prompt file to the context."),
    ] = False,
    output_path: Annotated[
        str | None,
        typer.Option("--output-path", "-o", help="Layout path. Defaults to <agents-dir>/layout.json."),
    ] = None,
    agents_dir: Annotated[
        str | None,
        typer.Option("--agents-dir", "-d", help="Agent work directory. Defaults to $HOME/code/machineconfig/.ai/agents/<job-name>."),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Whether to run in interactive mode, asking for missing parameters."),
    ] = False,
) -> None:
    defaults = get_update_installer_defaults(job_name=job_name)
    if not defaults.repo_root.joinpath("pyproject.toml").is_file():
        raise RuntimeError(f"Developer repo not found: {defaults.repo_root}")

    resolved_context_path = _resolve_context_path(context=context, context_path=context_path, defaults=defaults)
    resolved_prompt = _resolve_prompt(
        prompt=prompt,
        prompt_path=prompt_path,
        prompt_name=prompt_name,
        defaults=defaults,
    )
    resolved_prompt_path = _resolve_prompt_path(
        prompt=prompt,
        prompt_path=prompt_path,
        prompt_name=prompt_name,
    )
    resolved_agents_dir = _resolve_agents_dir(agents_dir=agents_dir, defaults=defaults)
    resolved_output_path = _resolve_output_path(
        output_path=output_path,
        resolved_agents_dir=resolved_agents_dir,
        defaults=defaults,
    )

    agents_create_impl(
        agent=agent,
        model=model,
        agent_load=agent_load,
        context=context,
        context_path=resolved_context_path,
        separator=separator,
        prompt=resolved_prompt,
        prompt_path=resolved_prompt_path,
        prompt_name=prompt_name,
        job_name=job_name,
        join_prompt_and_context=join_prompt_and_context,
        output_path=resolved_output_path,
        agents_dir=resolved_agents_dir,
        host=host,
        reasoning_effort=reasoning_effort,
        provider=provider,
        interactive=interactive,
    )


def get_app() -> typer.Typer:
    cli_app = typer.Typer(help="🤖 <a> Developer AI workflows.", no_args_is_help=True, add_help_option=True, add_completion=False)
    cli_app.command(
        name="update-installer",
        no_args_is_help=False,
        help="🔄 <u> Create an agents layout for updating installer_data.json.",
    )(update_installer)
    cli_app.command(name="u", no_args_is_help=False, hidden=True)(update_installer)
    return cli_app
