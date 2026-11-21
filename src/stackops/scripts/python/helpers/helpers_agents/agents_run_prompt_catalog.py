from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_run_types import PROMPTS_SOURCE


@dataclass(frozen=True, slots=True)
class PromptCatalogSource:
    source: str
    path: Path
    exists: bool
    prompt_count: int


@dataclass(frozen=True, slots=True)
class PromptCatalogEntry:
    name: str
    source: str
    path: Path
    group: str | None
    description: str | None
    agent: str | None
    directory: str | None
    text: str


@dataclass(frozen=True, slots=True)
class PromptCatalog:
    sources: tuple[PromptCatalogSource, ...]
    prompts: tuple[PromptCatalogEntry, ...]


def _entry_text_field(entry: object, keys: tuple[str, ...]) -> str | None:
    if not isinstance(entry, dict):
        return None
    fields = cast(dict[object, object], entry)
    for key in keys:
        value = fields.get(key)
        if isinstance(value, str) and value.strip() != "":
            return value.strip()
    return None


def collect_prompt_catalog(*, prompts_yaml_path: str | None, source: PROMPTS_SOURCE, group: str | None) -> PromptCatalog:
    from stackops.scripts.python.helpers.helpers_agents.agents_run_context import (
        collect_named_yaml_candidates,
        iter_named_yaml_entries,
        resolve_prompts_yaml_paths,
    )
    from stackops.utils.files.read import read_yaml

    sources: list[PromptCatalogSource] = []
    prompts: list[PromptCatalogEntry] = []
    for source_name, yaml_path in resolve_prompts_yaml_paths(prompts_yaml_path=prompts_yaml_path, source=source):
        if not yaml_path.is_file():
            sources.append(PromptCatalogSource(source=source_name, path=yaml_path, exists=False, prompt_count=0))
            continue
        yaml_data: object = read_yaml(yaml_path)
        if not isinstance(yaml_data, dict):
            raise ValueError(f"""Prompts YAML must be a mapping: {yaml_path}""")
        raw_entries = dict(iter_named_yaml_entries(raw_data=yaml_data, prefix=""))
        candidates = collect_named_yaml_candidates(raw_data=yaml_data, prefix="", group=group)
        sources.append(PromptCatalogSource(source=source_name, path=yaml_path, exists=True, prompt_count=len(candidates)))
        for name, (entry_group, text) in candidates.items():
            raw_entry = raw_entries[name]
            prompts.append(
                PromptCatalogEntry(
                    name=name,
                    source=source_name,
                    path=yaml_path,
                    group=entry_group,
                    description=_entry_text_field(raw_entry, ("description", "desc", "desciption")),
                    agent=_entry_text_field(raw_entry, ("agent",)),
                    directory=_entry_text_field(raw_entry, ("directory",)),
                    text=text,
                )
            )
    return PromptCatalog(sources=tuple(sources), prompts=tuple(prompts))
