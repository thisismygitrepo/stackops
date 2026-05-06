from pathlib import Path
import subprocess
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_impl import agents_create as agents_create_impl
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_SEAPRATOR, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from stackops.utils.source_of_truth import EXCLUDE_DIRS


DEFAULT_TEST_JOB_NAME = "updateTests"
UPDATE_TEST_PROMPT = """
/caveman wenyan
$caveman wenyan

Please write test file for the following files.
* 1 test file per py file.

* Your tests should go under: $repo_root/tests/mirror/$same_file_path_relative_to_repo_root
e.g. src/stackops/cluster/remote/file_manager.py
should have its test file at tests/mirror/src/stackops/cluster/remote/file_manager.py

* in your tests, you assume all types will be respected, so no need to experiment on that.
In other words, you only test for things that the strict harsh static type analyzer is still not capable of catching,
i.e. things that can only be determined at runtime. One example of these, if a file is reading another file,
static type anaylzer dones't know that other config file being read exists, we only know at runtime.
Especially if that config helper file should be withthin the repo itself, not passed by user,
so it must exist otherwise the repo is broken out of the box. I hope this was clear enough.
"""
_ADDITIONAL_EXCLUDED_CONTEXT_PARTS = frozenset({"tests"})
_EXCLUDED_CONTEXT_PARTS = frozenset(entry for entry in EXCLUDE_DIRS if "/" not in entry) | _ADDITIONAL_EXCLUDED_CONTEXT_PARTS


def get_developer_repo_root() -> Path:
    return Path.home().joinpath("code", "stackops")


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


def _should_include_python_context_path(*, relative_path: Path) -> bool:
    if relative_path.suffix != ".py":
        return False
    return not any(part in _EXCLUDED_CONTEXT_PARTS for part in relative_path.parts)


def _build_repo_python_context(*, repo_root: Path) -> str:
    context_entries = [
        relative_path.as_posix()
        for relative_path in _list_git_visible_files(repo_root=repo_root)
        if _should_include_python_context_path(relative_path=relative_path)
    ]
    if len(context_entries) == 0:
        raise RuntimeError(f"No Python context files found under {repo_root}")
    return DEFAULT_SEAPRATOR.join(context_entries)


def _resolve_prompt_options(
    *,
    prompt: str | None,
    prompt_path: str | None,
    prompt_name: str | None,
) -> tuple[str | None, str | None, str | None]:
    prompt_source_count = sum(source is not None for source in (prompt, prompt_path, prompt_name))
    if prompt_source_count > 1:
        raise typer.BadParameter("Use only one of --prompt, --prompt-path, or --prompt-name.")
    if prompt_source_count == 0:
        return UPDATE_TEST_PROMPT, None, None
    return prompt, prompt_path, prompt_name


def update_test(
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

    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else repo_root.joinpath(".ai", "agents", job_name)
    resolved_output_path = Path(output_path) if output_path is not None else resolved_agents_dir.joinpath("layout.json")
    context_content = _build_repo_python_context(repo_root=repo_root)
    context_output_path = resolved_agents_dir.joinpath("context.md")
    resolved_prompt, resolved_prompt_path, resolved_prompt_name = _resolve_prompt_options(
        prompt=prompt,
        prompt_path=prompt_path,
        prompt_name=prompt_name,
    )

    try:
        agents_create_impl(
            agent=agent,
            model=model,
            agent_load=agent_load,
            context=context_content,
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            prompt=resolved_prompt,
            prompt_path=resolved_prompt_path,
            prompt_name=resolved_prompt_name,
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
