from contextlib import chdir
from pathlib import Path
from typing import Annotated

import typer

import stackops.jobs.installer as installer_assets
from stackops.jobs.installer import INSTALLER_DATA_PATH_REFERENCE
from stackops.scripts.python.helpers.helpers_agents.agents_impl import agents_create as agents_create_impl
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from stackops.utils.path_reference import get_path_reference_library_relative_path


DEFAULT_INSTALLER_JOB_NAME = "updateInstallerData"
UPDATE_INSTALLER_SEPARATOR = "    },\n    {"


def get_developer_repo_root() -> Path:
    return Path.home().joinpath("code", "stackops")


def _get_installer_data_repo_relative_path() -> Path:
    return Path("src", "stackops").joinpath(
        get_path_reference_library_relative_path(module=installer_assets, path_reference=INSTALLER_DATA_PATH_REFERENCE)
    )


def _get_update_installer_prompt() -> str:
    installer_data_path = get_developer_repo_root().joinpath(_get_installer_data_repo_relative_path())
    return f"""For each assigned entry below, if repoURL is a GitHub repository, verify the release asset filename patterns.
Make sure fileNamePattern values match the current GitHub release assets.

modify the target file directly @ {installer_data_path}
Only work on entries assigned to you. Ignore the rest because other agents may be editing the same target file.

Notes:
* File patterns should never include a literal v before {{version}}, even if release assets include that v; the installer checks tag names with and without the leading v.
* If a fileNamePattern value is "<name>.py", it references a custom Python installer script. Do not touch it.
* If a fileNamePattern value is a custom package installation command, do not touch it.
* Do not touch any field other than fileNamePattern.
* If available, prefer musl over gnu Linux binaries because glibc versioning is problematic.
"""


def _ensure_prompt_override_is_unambiguous(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> None:
    provided_prompt_overrides = sum(value is not None for value in (prompt, prompt_path, prompt_name))
    if provided_prompt_overrides > 1:
        raise ValueError("Provide at most one of --prompt, --prompt-path, or --prompt-name")


def _resolve_prompt(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> str | None:
    if prompt is not None:
        return prompt
    if prompt_path is not None or prompt_name is not None:
        return None
    return _get_update_installer_prompt()


def _resolve_prompt_path(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> str | None:
    if prompt is not None or prompt_name is not None:
        return None
    return prompt_path


def _ensure_context_input_is_unambiguous(*, context: str | None, context_path: str | None) -> None:
    if context is not None and context_path is not None:
        raise ValueError("Provide at most one of --context or --context-path")


def _resolve_context_path(*, context: str | None, context_path: str | None, repo_root: Path) -> str | None:
    if context is not None:
        return None
    if context_path is not None:
        return context_path
    return str(repo_root.joinpath(_get_installer_data_repo_relative_path()))


def update_installer(
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent type.")] = "codex",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use, agent will use its default otherwise.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(
            "--reasoning",
            "-r",
            help="Reasoning effort for codex, copilot, and pi agents. Unsupported agents ignore it and use their default.",
        ),
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
            help="Context file or folder path. Defaults to src/stackops/jobs/installer/installer_data.json when --context is omitted.",
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
        typer.Option("--agents-dir", "-d", help="Agent work directory. Defaults to $HOME/code/stackops/.ai/agents/<job-name>."),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Whether to run in interactive mode, asking for missing parameters."),
    ] = False,
) -> None:
    repo_root = get_developer_repo_root()
    if not repo_root.joinpath("pyproject.toml").is_file():
        raise RuntimeError(f"Developer repo not found: {repo_root}")
    _ensure_prompt_override_is_unambiguous(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name)
    _ensure_context_input_is_unambiguous(context=context, context_path=context_path)

    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else repo_root.joinpath(".ai", "agents", job_name)
    resolved_output_path = Path(output_path) if output_path is not None else resolved_agents_dir.joinpath("layout.json")

    with chdir(repo_root):
        agents_create_impl(
            agent=agent,
            model=model,
            agent_load=agent_load,
            context=context,
            context_path=_resolve_context_path(context=context, context_path=context_path, repo_root=repo_root),
            separator=separator,
            prompt=_resolve_prompt(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name),
            prompt_path=_resolve_prompt_path(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name),
            prompt_name=prompt_name,
            job_name=job_name,
            join_prompt_and_context=join_prompt_and_context,
            output_path=str(resolved_output_path),
            agents_dir=str(resolved_agents_dir),
            host=host,
            reasoning_effort=reasoning_effort,
            provider=provider,
            interactive=interactive,
        )
