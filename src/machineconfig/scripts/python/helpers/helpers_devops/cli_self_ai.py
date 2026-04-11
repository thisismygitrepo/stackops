from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from machineconfig.scripts.python.helpers.helpers_agents.agents_impl import agents_create as agents_create_impl
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_SEAPRATOR, HOST, PROVIDER
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai_context import build_repo_python_context


DEFAULT_INSTALLER_JOB_NAME = "updateInstallerData"
DEFAULT_TEST_JOB_NAME = "updateTests"
UPDATE_INSTALLER_SEPARATOR = "    },\n    {"
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
UPDATE_TEST_PROMPT = """Please write test file for the following files.
* 1 test file per py file.
* Your tests should go under: $repo_root/tests/mirror/$same_file_path_relative_to_repo_root
* in your tests, you assume all types will be respected, so no need to experiment on that. In other words, you only test for things that the strict harsh static type analyzer is still not capable of catching, i.e. things that can only be determined at runtime. One example of these, if a file is reading another file, static type anaylzer dones't know that other config file being read exists, we only know at runtime. Especially if that config helper file should be withthin the repo itself, not passed by user, so it must exist otherwise the repo is broken out of the box. I hope this was clear enough.
"""
UPDATE_DOCS_PROMPT = """
Please update the docs @ $repo_root/docs with the following instructions:
* Only update the relevant docs to the files herein:

Do not touch the home page, quick start, 
"""


@dataclass(frozen=True)
class UpdateJobDefaults:
    repo_root: Path
    context_path: Path
    agents_dir: Path
    output_path: Path
    prompt: str


@dataclass(frozen=True)
class ForcedContext:
    content: str
    output_path: Path
    separator: str


def get_developer_repo_root() -> Path:
    return Path.home().joinpath("code", "machineconfig")


def _get_update_job_defaults(*, job_name: str, context_path: Path, prompt: str) -> UpdateJobDefaults:
    repo_root = get_developer_repo_root()
    agents_dir = repo_root.joinpath(".ai", "agents", job_name)
    return UpdateJobDefaults(
        repo_root=repo_root,
        context_path=context_path,
        agents_dir=agents_dir,
        output_path=agents_dir.joinpath("layout.json"),
        prompt=prompt,
    )


def get_update_installer_defaults(*, job_name: str) -> UpdateJobDefaults:
    repo_root = get_developer_repo_root()
    return _get_update_job_defaults(
        job_name=job_name,
        context_path=repo_root.joinpath("src", "machineconfig", "jobs", "installer", "installer_data.json"),
        prompt=UPDATE_INSTALLER_PROMPT,
    )


def get_update_test_defaults(*, job_name: str) -> UpdateJobDefaults:
    repo_root = get_developer_repo_root()
    return _get_update_job_defaults(
        job_name=job_name,
        context_path=repo_root.joinpath(".ai", "agents", job_name, "context.md"),
        prompt=UPDATE_TEST_PROMPT,
    )


def _build_update_test_forced_context(*, repo_root: Path, resolved_agents_dir: str) -> ForcedContext:
    return ForcedContext(
        content=build_repo_python_context(repo_root=repo_root, separator=DEFAULT_SEAPRATOR),
        output_path=Path(resolved_agents_dir).joinpath("context.md"),
        separator=DEFAULT_SEAPRATOR,
    )


def _resolve_context_path(*, context: str | None, context_path: str | None, defaults: UpdateJobDefaults) -> str | None:
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
    defaults: UpdateJobDefaults,
) -> str | None:
    if prompt is not None:
        return prompt
    if prompt_path is not None or prompt_name is not None:
        return None
    return defaults.prompt


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


def _resolve_agents_dir(*, agents_dir: str | None, defaults: UpdateJobDefaults) -> str:
    if agents_dir is not None:
        return agents_dir
    return str(defaults.agents_dir)


def _resolve_output_path(*, output_path: str | None, resolved_agents_dir: str, defaults: UpdateJobDefaults) -> str:
    if output_path is not None:
        return output_path
    if resolved_agents_dir != str(defaults.agents_dir):
        return str(Path(resolved_agents_dir).joinpath("layout.json"))
    return str(defaults.output_path)


def _run_update_job(
    *,
    defaults: UpdateJobDefaults,
    agent: AGENTS,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
    host: HOST,
    context: str | None,
    context_path: str | None,
    separator: str | None,
    agent_load: int,
    prompt: str | None,
    prompt_path: str | None,
    prompt_name: str | None,
    job_name: str,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    interactive: bool,
    forced_context_factory: Callable[[str], ForcedContext] | None = None,
) -> None:
    if not defaults.repo_root.joinpath("pyproject.toml").is_file():
        raise RuntimeError(f"Developer repo not found: {defaults.repo_root}")

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
    forced_context = None if forced_context_factory is None else forced_context_factory(resolved_agents_dir)
    if forced_context is None:
        if separator is None:
            raise ValueError("separator is required when no forced context is provided")
        resolved_context = context
        resolved_context_path = _resolve_context_path(context=context, context_path=context_path, defaults=defaults)
        resolved_separator = separator
    else:
        resolved_context = forced_context.content
        resolved_context_path = None
        resolved_separator = forced_context.separator

    try:
        agents_create_impl(
            agent=agent,
            model=model,
            agent_load=agent_load,
            context=resolved_context,
            context_path=resolved_context_path,
            separator=resolved_separator,
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
    finally:
        if forced_context is not None:
            forced_context.output_path.parent.mkdir(parents=True, exist_ok=True)
            forced_context.output_path.write_text(forced_context.content, encoding="utf-8")


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
    ] = UPDATE_INSTALLER_SEPARATOR,
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
    job_name: Annotated[str, typer.Option("--job-name", "-n", help="Job label and default output directory stem.")] = DEFAULT_INSTALLER_JOB_NAME,
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
    _run_update_job(
        agent=agent,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        host=host,
        context=context,
        context_path=context_path,
        separator=separator,
        agent_load=agent_load,
        prompt=prompt,
        prompt_path=prompt_path,
        prompt_name=prompt_name,
        job_name=job_name,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        interactive=interactive,
        defaults=get_update_installer_defaults(job_name=job_name),
    )


def update_test(
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent type.")] = "codex",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use, agent will use its default otherwise.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option("--reasoning-effort", "-r", help="Reasoning effort for codex agents. When omitted, codex uses its default."),
    ] = None,
    provider: Annotated[PROVIDER | None, typer.Option("--provider", "-v", help="Provider to use (if the agent supports many).")] = None,
    host: Annotated[HOST, typer.Option("--host", "-h", help="Machine to run agents on.")] = "local",
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", help="Number of tasks per prompt.")] = 10,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Prompt prefix as string.")] = None,
    prompt_path: Annotated[
        str | None,
        typer.Option(
            "--prompt-path",
            "-P",
            help="Prompt file path. When omitted, update-test uses its embedded default prompt unless --prompt or --prompt-name is provided.",
        ),
    ] = None,
    prompt_name: Annotated[str | None, typer.Option("--prompt-name", "-N", help="Prompt entry name from prompts YAML.")] = None,
    job_name: Annotated[str, typer.Option("--job-name", "-n", help="Job label and default output directory stem.")] = DEFAULT_TEST_JOB_NAME,
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
    defaults = get_update_test_defaults(job_name=job_name)
    _run_update_job(
        agent=agent,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        host=host,
        context=None,
        context_path=None,
        separator=None,
        agent_load=agent_load,
        prompt=prompt,
        prompt_path=prompt_path,
        prompt_name=prompt_name,
        job_name=job_name,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        interactive=interactive,
        defaults=defaults,
        forced_context_factory=lambda resolved_agents_dir: _build_update_test_forced_context(
            repo_root=defaults.repo_root,
            resolved_agents_dir=resolved_agents_dir,
        ),
    )


def get_app() -> typer.Typer:
    cli_app = typer.Typer(help="🤖 <a> Developer AI workflows.", no_args_is_help=True, add_help_option=True, add_completion=False)
    cli_app.command(
        name="update-installer",
        no_args_is_help=False,
        help="🔄 <u> Create an agents layout for updating installer_data.json.",
    )(update_installer)
    cli_app.command(name="u", no_args_is_help=False, hidden=True)(update_installer)
    cli_app.command(
        name="update-test",
        no_args_is_help=False,
        help="🧪 <t> Create an agents layout for writing tests from repo Python sources.",
    )(update_test)
    cli_app.command(name="t", no_args_is_help=False, hidden=True)(update_test)
    return cli_app
