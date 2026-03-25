from dataclasses import dataclass
from pathlib import Path
from typing import cast

from machineconfig.scripts.python.helpers.helpers_agents.agents_create_artifacts import (
    ContextSourceKind,
    CreateContextDirectoryEntry,
    PromptSourceKind,
)


def _split_and_chunk_prompts(raw_material: str, separator: str, tasks_per_prompt: int) -> list[str]:
    prompts = [piece for piece in raw_material.split(separator) if piece.strip() != ""]
    if not prompts:
        return []
    if tasks_per_prompt <= 0:
        raise ValueError("--agent-load must be a positive integer")
    if tasks_per_prompt >= len(prompts):
        print("No need to chunk prompts, as tasks_per_prompt >= total prompts.", f"({tasks_per_prompt} >= {len(prompts)})")
        return prompts
    print(f"Chunking {len(prompts)} prompts into groups of {tasks_per_prompt} rows/tasks each.")
    grouped: list[str] = []
    for idx in range(0, len(prompts), tasks_per_prompt):
        grouped.append(separator.join(prompts[idx : idx + tasks_per_prompt]))
    return grouped


@dataclass(frozen=True, slots=True)
class ResolvedPromptInput:
    prompt_text: str
    source_kind: PromptSourceKind
    source_path: Path | None


@dataclass(frozen=True, slots=True)
class ResolvedContextInput:
    prompt_materials: list[str]
    source_kind: ContextSourceKind
    source_path: Path | None
    file_content: str | None
    directory_entries: tuple[CreateContextDirectoryEntry, ...]


def resolve_prompt_input(*, prompt: str | None, prompt_path: str | None) -> ResolvedPromptInput:
    prompt_options = [prompt, prompt_path]
    provided_prompt = [opt for opt in prompt_options if opt is not None]
    if len(provided_prompt) != 1:
        raise ValueError("Exactly one of --prompt or --prompt-path must be provided")

    if prompt_path is None:
        return ResolvedPromptInput(prompt_text=cast(str, prompt), source_kind="inline_text", source_path=None)

    prompt_path_resolved = Path(prompt_path).expanduser().resolve()
    if not prompt_path_resolved.exists() or not prompt_path_resolved.is_file():
        raise ValueError(f"Path does not exist: {prompt_path_resolved}")
    return ResolvedPromptInput(
        prompt_text=prompt_path_resolved.read_text(encoding="utf-8"),
        source_kind="file_path",
        source_path=prompt_path_resolved,
    )


def resolve_context_input(
    *,
    context: str | None,
    context_path: str | None,
    separator: str,
    agent_load: int,
    agents_dir_obj: Path,
) -> ResolvedContextInput:
    context_options = [context, context_path]
    provided_context = [opt for opt in context_options if opt is not None]
    if len(provided_context) > 1:
        raise ValueError("Provide at most one of --context or --context-path")

    if context is not None:
        prompt_materials = _split_and_chunk_prompts(raw_material=context, separator=separator, tasks_per_prompt=agent_load)
        if not prompt_materials:
            raise ValueError("Provided --context does not contain any non-empty task after splitting")
        return ResolvedContextInput(
            prompt_materials=prompt_materials,
            source_kind="inline_text",
            source_path=None,
            file_content=context,
            directory_entries=(),
        )

    if context_path is None:
        context_path_resolved = agents_dir_obj / "context.md"
    else:
        context_path_resolved = Path(context_path).expanduser().resolve()
    if not context_path_resolved.exists():
        raise ValueError(f"Path does not exist: {context_path_resolved}")

    if context_path_resolved.is_file():
        context_file_content = context_path_resolved.read_text(encoding="utf-8", errors="ignore")
        prompt_materials = _split_and_chunk_prompts(raw_material=context_file_content, separator=separator, tasks_per_prompt=agent_load)
        return ResolvedContextInput(
            prompt_materials=prompt_materials,
            source_kind="file_path",
            source_path=context_path_resolved,
            file_content=context_file_content,
            directory_entries=(),
        )

    if not context_path_resolved.is_dir():
        raise ValueError(f"Path is neither file nor directory: {context_path_resolved}")

    files = sorted(
        (file_path for file_path in context_path_resolved.rglob("*") if file_path.is_file()),
        key=lambda path: str(path.relative_to(context_path_resolved)),
    )
    if not files:
        raise ValueError(f"No files found in directory: {context_path_resolved}")

    file_materials: list[str] = []
    directory_entries: list[CreateContextDirectoryEntry] = []
    for file_path in files:
        file_content = file_path.read_text(encoding="utf-8")
        file_materials.append(file_content)
        directory_entries.append(
            CreateContextDirectoryEntry(
                relative_path=file_path.relative_to(context_path_resolved).as_posix(),
                content=file_content,
            )
        )

    non_empty_materials = [material for material in file_materials if material.strip() != ""]
    if not non_empty_materials:
        raise ValueError(f"All files in directory are empty: {context_path_resolved}")
    if agent_load <= 0:
        raise ValueError("--agent-load must be a positive integer")
    if agent_load >= len(non_empty_materials):
        print("No need to chunk prompts, as tasks_per_prompt >= total prompts.", f"({agent_load} >= {len(non_empty_materials)})")
        prompt_materials = non_empty_materials
    else:
        print(f"Chunking {len(non_empty_materials)} directory files into groups of {agent_load} rows/tasks each.")
        prompt_materials = [
            separator.join(non_empty_materials[idx : idx + agent_load])
            for idx in range(0, len(non_empty_materials), agent_load)
        ]
    return ResolvedContextInput(
        prompt_materials=prompt_materials,
        source_kind="directory_path",
        source_path=context_path_resolved,
        file_content=None,
        directory_entries=tuple(directory_entries),
    )


def resolve_agents_output_dir(*, repo_root: Path, agents_dir: str | None, job_name: str | None) -> tuple[Path, str]:
    if agents_dir is None:
        from machineconfig.utils.accessories import randstr

        if job_name is None:
            job_name_resolved = randstr(6)
        else:
            job_name_resolved = job_name.strip()
        return Path(repo_root) / ".ai" / "agents" / job_name_resolved, job_name_resolved

    agents_dir_obj = Path(agents_dir).expanduser().resolve().absolute()
    if job_name is None:
        job_name_resolved = agents_dir_obj.name
    else:
        job_name_resolved = job_name.strip()
    return agents_dir_obj, job_name_resolved
