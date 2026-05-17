import json
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import stackops.scripts.python.helpers.helpers_agents.agents_shell as agent_shell
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_STAGGER_MAX, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


PromptSourceKind: TypeAlias = Literal["inline_text", "file_path", "yaml_name"]
ContextSourceKind: TypeAlias = Literal["inline_text", "file_path", "directory_path"]


@dataclass(frozen=True, slots=True)
class CreateContextDirectoryEntry:
    relative_path: str
    content: str


@dataclass(frozen=True, slots=True)
class CreatePromptArtifactsInput:
    source_kind: PromptSourceKind
    source_path: Path | None
    source_name: str | None
    content: str


@dataclass(frozen=True, slots=True)
class CreateContextArtifactsInput:
    source_kind: ContextSourceKind
    source_path: Path | None
    file_content: str | None
    directory_entries: tuple[CreateContextDirectoryEntry, ...]


@dataclass(frozen=True, slots=True)
class CreateArtifactsOutput:
    artifacts_dir: Path
    prompt_snapshot_path: Path
    context_snapshot_path: Path
    manifest_path: Path
    recreate_script_path: Path
    recreate_command: str
    recreate_command_args: tuple[str, ...]


def _separator_cli_value(separator: str) -> str:
    return separator.encode("unicode_escape").decode("ascii")


def _write_context_snapshot(*, artifacts_dir: Path, context: CreateContextArtifactsInput) -> Path:
    if context.source_kind == "directory_path":
        snapshot_dir = artifacts_dir / "context"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for entry in context.directory_entries:
            entry_path = snapshot_dir / entry.relative_path
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            entry_path.write_text(entry.content, encoding="utf-8")
        return snapshot_dir

    if context.file_content is None:
        raise ValueError("file_content must be provided for non-directory context snapshots")
    snapshot_path = artifacts_dir / "context.md"
    snapshot_path.write_text(context.file_content, encoding="utf-8")
    return snapshot_path


def _resolve_recreate_source_path(*, source_path: Path | None, snapshot_path: Path) -> Path:
    if source_path is None:
        return snapshot_path
    return source_path


def _build_recreate_command_args(
    *,
    agent: AGENTS,
    host: HOST,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
    agent_load: int,
    separator: str,
    prompt_source_kind: PromptSourceKind,
    prompt_recreate_path: Path,
    prompt_name: str | None,
    context_recreate_path: Path,
    job_name: str,
    join_prompt_and_context: bool,
    run: bool,
    layout_output_path: Path,
    agents_dir: Path,
    stagger_max: float,
) -> list[str]:
    command: list[str] = [
        "uv",
        "run",
        "agents",
        "parallel",
        "create",
        "--agent",
        agent,
        "--host",
        host,
        "--context-path",
        str(context_recreate_path),
        "--separator",
        _separator_cli_value(separator),
        "--agent-load",
        str(agent_load),
        "--stagger-max",
        f"{stagger_max:g}",
        "--job-name",
        job_name,
        "--output-path",
        str(layout_output_path),
        "--agents-dir",
        str(agents_dir),
    ]
    if prompt_source_kind == "yaml_name":
        if prompt_name is None:
            raise ValueError("prompt_name must be provided when prompt source_kind is 'yaml_name'")
        command.extend(["--prompt-name", prompt_name])
    else:
        command.extend(["--prompt-path", str(prompt_recreate_path)])
    if model is not None:
        command.extend(["--model", model])
    if reasoning_effort is not None:
        command.extend(["--reasoning", reasoning_effort])
    if provider is not None:
        command.extend(["--provider", provider])
    if join_prompt_and_context:
        command.append("--joined-prompt-context")
    if run:
        command.append("--run")
    return command


_RECREATE_PATH_FLAGS = frozenset({"--context-path", "--prompt-path", "--output-path", "--agents-dir"})


def _render_shell_path(*, path: Path, repo_root: Path, home_dir: Path, allow_repo_relative: bool) -> str:
    if allow_repo_relative:
        try:
            relative_to_repo = path.relative_to(repo_root)
        except ValueError:
            pass
        else:
            relative_text = relative_to_repo.as_posix()
            return "." if relative_text == "." else shlex.quote(relative_text)

    try:
        relative_to_home = path.relative_to(home_dir)
    except ValueError:
        return shlex.quote(str(path))

    relative_text = relative_to_home.as_posix()
    if relative_text == ".":
        return "$HOME"
    return f"""$HOME{shlex.quote(f"/{relative_text}")}"""


def _build_posix_recreate_command(*, repo_root: Path, recreate_command_args: list[str]) -> str:
    repo_root_resolved = repo_root.resolve()
    home_dir = Path.home().resolve()
    rendered_args: list[str] = []
    previous_arg: str | None = None
    for arg in recreate_command_args:
        if previous_arg in _RECREATE_PATH_FLAGS:
            rendered_args.append(_render_shell_path(path=Path(arg), repo_root=repo_root_resolved, home_dir=home_dir, allow_repo_relative=True))
        else:
            rendered_args.append(shlex.quote(arg))
        previous_arg = arg
    repo_root_shell_path = _render_shell_path(path=repo_root_resolved, repo_root=repo_root_resolved, home_dir=home_dir, allow_repo_relative=False)
    command_segments = _group_posix_command_segments(raw_args=recreate_command_args, rendered_args=rendered_args)
    return " \\\n    ".join([f"cd {repo_root_shell_path} &&", *command_segments])


def _group_posix_command_segments(*, raw_args: list[str], rendered_args: list[str]) -> list[str]:
    if len(raw_args) != len(rendered_args):
        raise ValueError("raw_args and rendered_args must have the same length")
    if len(rendered_args) < 5:
        return [" ".join(rendered_args)]

    grouped_segments: list[str] = [" ".join(rendered_args[:5])]
    index = 5
    while index < len(raw_args):
        raw_arg = raw_args[index]
        rendered_arg = rendered_args[index]
        next_index = index + 1
        if raw_arg.startswith("--") and next_index < len(raw_args) and not raw_args[next_index].startswith("--"):
            grouped_segments.append(f"{rendered_arg} {rendered_args[next_index]}")
            index += 2
            continue
        grouped_segments.append(rendered_arg)
        index += 1
    return grouped_segments


def _build_powershell_recreate_command(*, repo_root: Path, recreate_command_args: list[str]) -> str:
    repo_root_shell_path = agent_shell.quote_for_shell(str(repo_root.resolve()), is_windows=True)
    recreate_invocation = agent_shell.build_shell_invocation(
        executable=recreate_command_args[0], arguments=recreate_command_args[1:], is_windows=True
    )
    return f"""Set-Location -LiteralPath {repo_root_shell_path}
{recreate_invocation}"""


def _build_recreate_command(*, repo_root: Path, recreate_command_args: list[str]) -> str:
    if agent_shell.is_windows_host():
        return _build_powershell_recreate_command(repo_root=repo_root, recreate_command_args=recreate_command_args)
    return _build_posix_recreate_command(repo_root=repo_root, recreate_command_args=recreate_command_args)


def write_create_artifacts(
    *,
    repo_root: Path,
    agents_dir: Path,
    layout_output_path: Path,
    agent: AGENTS,
    host: HOST,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
    agent_load: int,
    separator: str,
    prompt: CreatePromptArtifactsInput,
    context: CreateContextArtifactsInput,
    job_name: str,
    join_prompt_and_context: bool,
    run: bool,
    stagger_max: float = DEFAULT_STAGGER_MAX,
) -> CreateArtifactsOutput:
    artifacts_dir = agents_dir / ".create"
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    prompt_snapshot_path = artifacts_dir / "prompt.md"
    prompt_snapshot_path.write_text(prompt.content, encoding="utf-8")
    context_snapshot_path = _write_context_snapshot(artifacts_dir=artifacts_dir, context=context)
    prompt_recreate_path = _resolve_recreate_source_path(source_path=prompt.source_path, snapshot_path=prompt_snapshot_path)
    context_recreate_path = _resolve_recreate_source_path(source_path=context.source_path, snapshot_path=context_snapshot_path)

    recreate_command_args = _build_recreate_command_args(
        agent=agent,
        host=host,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        agent_load=agent_load,
        separator=separator,
        prompt_source_kind=prompt.source_kind,
        prompt_recreate_path=prompt_recreate_path,
        prompt_name=prompt.source_name,
        context_recreate_path=context_recreate_path,
        job_name=job_name,
        join_prompt_and_context=join_prompt_and_context,
        run=run,
        layout_output_path=layout_output_path,
        agents_dir=agents_dir,
        stagger_max=stagger_max,
    )
    recreate_command = _build_recreate_command(repo_root=repo_root, recreate_command_args=recreate_command_args)

    is_windows = agent_shell.is_windows_host()
    recreate_script_path = artifacts_dir / agent_shell.get_recreate_script_filename(is_windows=is_windows)
    if is_windows:
        recreate_script_contents = f"""$ErrorActionPreference = 'Stop'

{recreate_command}
"""
    else:
        recreate_script_contents = f"""#!/usr/bin/env bash
# set -euo pipefail

{recreate_command}
"""
    recreate_script_path.write_text(recreate_script_contents, encoding="utf-8")
    recreate_script_path.chmod(0o755)

    manifest_path = artifacts_dir / "manifest.json"
    manifest = {
        "repo_root": str(repo_root),
        "agents_dir": str(agents_dir),
        "layout_output_path": str(layout_output_path),
        "job_name": job_name,
        "agent": agent,
        "host": host,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "provider": provider,
        "agent_load": agent_load,
        "stagger_max": stagger_max,
        "separator": separator,
        "separator_cli_value": _separator_cli_value(separator),
        "join_prompt_and_context": join_prompt_and_context,
        "run": run,
        "prompt": {
            "source_kind": prompt.source_kind,
            "source_path": None if prompt.source_path is None else str(prompt.source_path),
            "source_name": prompt.source_name,
            "snapshot_path": str(prompt_snapshot_path),
        },
        "context": {
            "source_kind": context.source_kind,
            "source_path": None if context.source_path is None else str(context.source_path),
            "snapshot_path": str(context_snapshot_path),
            "snapshot_relative_paths": [entry.relative_path for entry in context.directory_entries],
        },
        "recreate_command": recreate_command,
        "recreate_command_args": recreate_command_args,
        "recreate_script_path": str(recreate_script_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=4), encoding="utf-8")

    return CreateArtifactsOutput(
        artifacts_dir=artifacts_dir,
        prompt_snapshot_path=prompt_snapshot_path,
        context_snapshot_path=context_snapshot_path,
        manifest_path=manifest_path,
        recreate_script_path=recreate_script_path,
        recreate_command=recreate_command,
        recreate_command_args=tuple(recreate_command_args),
    )
