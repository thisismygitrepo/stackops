import json
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


PromptSourceKind: TypeAlias = Literal["inline_text", "file_path"]
ContextSourceKind: TypeAlias = Literal["inline_text", "file_path", "directory_path"]


@dataclass(frozen=True, slots=True)
class CreateContextDirectoryEntry:
    relative_path: str
    content: str


@dataclass(frozen=True, slots=True)
class CreatePromptArtifactsInput:
    source_kind: PromptSourceKind
    source_path: Path | None
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


def _build_recreate_command_args(
    *,
    agent: AGENTS,
    host: HOST,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
    agent_load: int,
    separator: str,
    prompt_snapshot_path: Path,
    context_snapshot_path: Path,
    job_name: str,
    join_prompt_and_context: bool,
    layout_output_path: Path,
    agents_dir: Path,
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
        str(context_snapshot_path),
        "--separator",
        _separator_cli_value(separator),
        "--agent-load",
        str(agent_load),
        "--prompt-path",
        str(prompt_snapshot_path),
        "--job-name",
        job_name,
        "--output-path",
        str(layout_output_path),
        "--agents-dir",
        str(agents_dir),
    ]
    if model is not None:
        command.extend(["--model", model])
    if reasoning_effort is not None:
        command.extend(["--reasoning-effort", reasoning_effort])
    if provider is not None:
        command.extend(["--provider", provider])
    if join_prompt_and_context:
        command.append("--joined-prompt-context")
    return command


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
) -> CreateArtifactsOutput:
    artifacts_dir = agents_dir / ".create"
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    prompt_snapshot_path = artifacts_dir / "prompt.md"
    prompt_snapshot_path.write_text(prompt.content, encoding="utf-8")
    context_snapshot_path = _write_context_snapshot(artifacts_dir=artifacts_dir, context=context)

    recreate_command_args = _build_recreate_command_args(
        agent=agent,
        host=host,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        agent_load=agent_load,
        separator=separator,
        prompt_snapshot_path=prompt_snapshot_path,
        context_snapshot_path=context_snapshot_path,
        job_name=job_name,
        join_prompt_and_context=join_prompt_and_context,
        layout_output_path=layout_output_path,
        agents_dir=agents_dir,
    )
    recreate_command = f"""cd {shlex.quote(str(repo_root))} && {shlex.join(recreate_command_args)}"""

    recreate_script_path = artifacts_dir / "recreate_layout.sh"
    recreate_script_path.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail

{recreate_command}
""",
        encoding="utf-8",
    )
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
        "separator": separator,
        "separator_cli_value": _separator_cli_value(separator),
        "join_prompt_and_context": join_prompt_and_context,
        "prompt": {
            "source_kind": prompt.source_kind,
            "source_path": None if prompt.source_path is None else str(prompt.source_path),
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
