from typing import Final, TypedDict

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, DEFAULT_SEAPRATOR, DEFAULT_STAGGER_MAX, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_backend import AgentParallelBackend, DEFAULT_AGENT_PARALLEL_BACKEND
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


PARALLEL_CREATE_COMMAND_NAME: Final[str] = "agents parallel create"
PARALLEL_RUN_COMMAND_NAME: Final[str] = "agents parallel run-parallel"
PARALLEL_YAML_TEMPLATE_ENTRY_NAME: Final[str] = "entryExample"
_ESCAPED_DEFAULT_SEPARATOR: Final[str] = DEFAULT_SEAPRATOR.encode("unicode_escape").decode("ascii")


class ParallelCreateYamlEntry(TypedDict):
    agent: AGENTS | None
    model: str | None
    reasoning: ReasoningEffort | None
    provider: PROVIDER | None
    host: HOST | None
    backend: AgentParallelBackend | None
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
PARALLEL_YAML_TEMPLATE_DEFAULT_ENTRY: Final[ParallelCreateYamlEntry] = {
    "agent": "codex",
    "model": None,
    "reasoning": None,
    "provider": None,
    "host": "local",
    "backend": DEFAULT_AGENT_PARALLEL_BACKEND,
    "context": None,
    "context_path": None,
    "separator": _ESCAPED_DEFAULT_SEPARATOR,
    "agent_load": 3,
    "stagger_max": DEFAULT_STAGGER_MAX,
    "prompt": None,
    "prompt_path": None,
    "prompt_name": None,
    "job_name": "AI_Agents",
    "join_prompt_and_context": False,
    "run": False,
    "output_path": None,
    "agents_dir": None,
    "interactive": False,
}
