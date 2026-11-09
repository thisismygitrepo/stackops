from typing import Final, TypedDict, cast

from stackops.utils.schemas.fire_agents.fire_agents_types import (
    AGENTS,
    HOST,
    PROVIDER,
    ReasoningEffort,
)
from stackops.utils.schemas.config.multiplexer_types import AgentLaunchBackend


PARALLEL_CREATE_COMMAND_NAME: Final[str] = "agents parallel create"
PARALLEL_RUN_COMMAND_NAME: Final[str] = "agents parallel run"
PARALLEL_YAML_TEMPLATE_ENTRY_NAME: Final[str] = "entryExample"


class ParallelCreateYamlEntry(TypedDict):
    agent: AGENTS | None
    model: str | None
    reasoning: ReasoningEffort | None
    provider: PROVIDER | None
    host: HOST | None
    backend: AgentLaunchBackend | None
    context: str | None
    context_path: str | None
    separator: str | None
    agent_load: int | None
    stagger_max: float | None
    prompt: str | None
    prompt_path: str | None
    prompt_name: str | None
    job_name: str | None
    join_prompt_and_context: bool | None
    run: bool | None
    output_path: str | None
    agents_dir: str | None
    interactive: bool | None


PARALLEL_CREATE_CONFIG_KEYS: Final[frozenset[str]] = frozenset(ParallelCreateYamlEntry.__annotations__.keys())


def parallel_yaml_default_entry() -> ParallelCreateYamlEntry:
    import yaml

    from stackops.utils.managed_files import get_managed_file_spec

    spec = get_managed_file_spec("parallel")
    entries = cast(dict[str, ParallelCreateYamlEntry], yaml.safe_load(spec.example_source_path.read_text(encoding="utf-8")))
    return entries[PARALLEL_YAML_TEMPLATE_ENTRY_NAME]
