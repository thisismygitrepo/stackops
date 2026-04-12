from pathlib import Path
import subprocess
from typing import Annotated

import typer

from machineconfig.scripts.python.helpers.helpers_agents.agents_impl import agents_create as agents_create_impl
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_SEAPRATOR, HOST, PROVIDER
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


DEFAULT_DOCS_JOB_NAME = "updateDocs"
UPDATE_DOCS_PROMPT = """Please update documentation for the following files.
* Only edit files under docs/cli and docs/api.
* Do not touch docs/index.md, docs/quickstart.md, docs/guide/**, Home, User Guide, or any other documentation tab.
* Treat each context entry as a documentation file path that you should update directly.
* Inspect the relevant Python sources and current CLI or API behavior as needed to keep those docs accurate.
* Prefer the one current behavior implemented in the repo. Remove stale wording instead of documenting fallback or legacy behavior.
"""
_ALLOWED_DOCS_CONTEXT_ROOTS = (Path("docs", "cli"), Path("docs", "api"))


def get_developer_repo_root() -> Path:
    return Path.home().joinpath("code", "machineconfig")


def _list_git_visible_files(*, repo_root: Path) -> tuple[Path, ...]:
    completed_process = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--full-name"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed_process.returncode != 0:
        stderr = completed_process.stderr.strip()
        stdout = completed_process.stdout.strip()
        details = stderr or stdout or "unknown error"
        raise RuntimeError(f"Failed to enumerate repository files for {repo_root}: {details}")

    visible_files: list[Path] = []
    seen_paths: set[Path] = set()
    for raw_line in completed_process.stdout.splitlines():
        normalized_line = raw_line.strip()
        if normalized_line == "":
            continue
        relative_path = Path(normalized_line)
        if relative_path in seen_paths:
            continue
        seen_paths.add(relative_path)
        visible_files.append(relative_path)
    return tuple(sorted(visible_files, key=lambda path: path.as_posix()))


def should_include_docs_context_path(*, relative_path: Path) -> bool:
    if relative_path.suffix != ".md":
        return False
    return any(relative_path.is_relative_to(allowed_root) for allowed_root in _ALLOWED_DOCS_CONTEXT_ROOTS)


def _build_docs_context(*, repo_root: Path) -> str:
    context_entries = [
        relative_path.as_posix()
        for relative_path in _list_git_visible_files(repo_root=repo_root)
        if should_include_docs_context_path(relative_path=relative_path)
    ]
    if len(context_entries) == 0:
        raise RuntimeError(f"No docs context files found under {repo_root}")
    return DEFAULT_SEAPRATOR.join(context_entries)


def _resolve_prompt(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> str | None:
    if prompt is not None:
        return prompt
    if prompt_path is not None or prompt_name is not None:
        return None
    return UPDATE_DOCS_PROMPT


def _resolve_prompt_path(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> str | None:
    if prompt is not None or prompt_name is not None:
        return None
    return prompt_path


def update_docs(
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
            help="Prompt file path. When omitted, update-docs uses its embedded default prompt unless --prompt or --prompt-name is provided.",
        ),
    ] = None,
    prompt_name: Annotated[str | None, typer.Option("--prompt-name", "-N", help="Prompt entry name from prompts YAML.")] = None,
    job_name: Annotated[str, typer.Option("--job-name", "-n", help="Job label and default output directory stem.")] = DEFAULT_DOCS_JOB_NAME,
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
    repo_root = get_developer_repo_root()
    if not repo_root.joinpath("pyproject.toml").is_file():
        raise RuntimeError(f"Developer repo not found: {repo_root}")

    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else repo_root.joinpath(".ai", "agents", job_name)
    resolved_output_path = Path(output_path) if output_path is not None else resolved_agents_dir.joinpath("layout.json")
    context_content = _build_docs_context(repo_root=repo_root)
    context_output_path = resolved_agents_dir.joinpath("context.md")

    try:
        agents_create_impl(
            agent=agent,
            model=model,
            agent_load=agent_load,
            context=context_content,
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
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
    finally:
        context_output_path.parent.mkdir(parents=True, exist_ok=True)
        context_output_path.write_text(context_content, encoding="utf-8")
