import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, HOST, PROVIDER, ReasoningEffort


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
    snapshot_suffix = ".json" if context.source_path is not None and context.source_path.suffix == ".json" else ".md"
    snapshot_path = artifacts_dir / f"""context{snapshot_suffix}"""
    snapshot_path.write_text(context.file_content, encoding="utf-8")
    return snapshot_path


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
    stagger_max: float,
) -> CreateArtifactsOutput:
    artifacts_dir = agents_dir / ".create"
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    prompt_snapshot_path = artifacts_dir / "prompt.md"
    prompt_snapshot_path.write_text(prompt.content, encoding="utf-8")
    context_snapshot_path = _write_context_snapshot(artifacts_dir=artifacts_dir, context=context)

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
        "join_prompt_and_context": join_prompt_and_context,
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
    }
    manifest_path.write_text(json.dumps(manifest, indent=4), encoding="utf-8")

    return CreateArtifactsOutput(
        artifacts_dir=artifacts_dir,
        prompt_snapshot_path=prompt_snapshot_path,
        context_snapshot_path=context_snapshot_path,
        manifest_path=manifest_path,
    )
