from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas import (
    PARALLEL_CREATE_CONFIG_KEYS,
    ensure_stackops_yaml_schema_exists,
)
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_SEAPRATOR, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from stackops.utils.yaml_schema import yaml_language_server_schema_comment


PARALLEL_RUNS_WHERE: TypeAlias = Literal["all", "a", "repo", "r", "private", "p", "public", "b", "library", "l"]
_PARALLEL_YAML_FILE_NAME: Final[str] = "parallel.yaml"
_REPO_STACKOPS_DIRECTORY_NAME: Final[str] = ".stackops"
CREATE_CONFIG_KEYS: Final[frozenset[str]] = PARALLEL_CREATE_CONFIG_KEYS


@dataclass(frozen=True, slots=True)
class ParallelCreateValues:
    agent: AGENTS | None
    model: str | None
    reasoning_effort: ReasoningEffort | None
    provider: PROVIDER | None
    host: HOST | None
    context: str | None
    context_path: str | None
    separator: str | None
    agent_load: int | None
    prompt: str | None
    prompt_path: str | None
    prompt_name: str | None
    job_name: str | None
    join_prompt_and_context: bool | None
    output_path: str | None
    agents_dir: str | None
    interactive: bool | None


@dataclass(frozen=True, slots=True)
class ResolvedParallelCreateValues:
    agent: AGENTS
    model: str | None
    reasoning_effort: ReasoningEffort | None
    provider: PROVIDER | None
    host: HOST
    context: str | None
    context_path: str | None
    separator: str
    agent_load: int
    prompt: str | None
    prompt_path: str | None
    prompt_name: str | None
    job_name: str
    join_prompt_and_context: bool
    output_path: str | None
    agents_dir: str | None
    interactive: bool


def empty_parallel_create_values() -> ParallelCreateValues:
    return ParallelCreateValues(
        agent=None,
        model=None,
        reasoning_effort=None,
        provider=None,
        host=None,
        context=None,
        context_path=None,
        separator=None,
        agent_load=None,
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name=None,
        join_prompt_and_context=None,
        output_path=None,
        agents_dir=None,
        interactive=None,
    )


def merge_parallel_create_values(*, base: ParallelCreateValues, overrides: ParallelCreateValues) -> ResolvedParallelCreateValues:
    agent = overrides.agent if overrides.agent is not None else base.agent
    host = overrides.host if overrides.host is not None else base.host
    separator = overrides.separator if overrides.separator is not None else base.separator
    agent_load = overrides.agent_load if overrides.agent_load is not None else base.agent_load
    job_name = overrides.job_name if overrides.job_name is not None else base.job_name
    join_prompt_and_context = (
        overrides.join_prompt_and_context if overrides.join_prompt_and_context is not None else base.join_prompt_and_context
    )
    interactive = overrides.interactive if overrides.interactive is not None else base.interactive
    if agent_load is not None and agent_load <= 0:
        raise ValueError("agent_load must be a positive integer")
    resolved_separator = DEFAULT_SEAPRATOR if separator is None else separator
    return ResolvedParallelCreateValues(
        agent="codex" if agent is None else agent,
        model=overrides.model if overrides.model is not None else base.model,
        reasoning_effort=overrides.reasoning_effort if overrides.reasoning_effort is not None else base.reasoning_effort,
        provider=overrides.provider if overrides.provider is not None else base.provider,
        host="local" if host is None else host,
        context=overrides.context if overrides.context is not None else base.context,
        context_path=overrides.context_path if overrides.context_path is not None else base.context_path,
        separator=decode_separator_value(separator=resolved_separator),
        agent_load=3 if agent_load is None else agent_load,
        prompt=overrides.prompt if overrides.prompt is not None else base.prompt,
        prompt_path=overrides.prompt_path if overrides.prompt_path is not None else base.prompt_path,
        prompt_name=overrides.prompt_name if overrides.prompt_name is not None else base.prompt_name,
        job_name="AI_Agents" if job_name is None else job_name,
        join_prompt_and_context=False if join_prompt_and_context is None else join_prompt_and_context,
        output_path=overrides.output_path if overrides.output_path is not None else base.output_path,
        agents_dir=overrides.agents_dir if overrides.agents_dir is not None else base.agents_dir,
        interactive=False if interactive is None else interactive,
    )


def decode_separator_value(*, separator: str) -> str:
    try:
        return bytes(separator, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return separator


def parallel_yaml_template() -> str:
    return parallel_yaml_template_for_path(yaml_path=Path(_PARALLEL_YAML_FILE_NAME))


def parallel_yaml_header_for_path(*, yaml_path: Path) -> str:
    return f"""{yaml_language_server_schema_comment(yaml_path=yaml_path)}
# parallel.yaml used by `agents parallel run-parallel`
# Top-level keys are run names. Select nested entries with dot paths, e.g. docs.update.
# Each run entry uses the same option names as `agents parallel create`.
"""


def parallel_yaml_template_for_path(*, yaml_path: Path) -> str:
    return f"""{parallel_yaml_header_for_path(yaml_path=yaml_path)}
default:
  agent: codex
  model: null
  reasoning_effort: high
  provider: openai
  host: local
  context: null
  context_path: ./.ai/agents/default/context.md
  separator: "\\n@-@\\n"
  agent_load: 3
  prompt: null
  prompt_path: ./.ai/prompts/default.md
  prompt_name: null
  job_name: default
  join_prompt_and_context: false
  output_path: null
  agents_dir: null
  interactive: false
"""


def resolve_parallel_yaml_paths(*, parallel_yaml_path: str | None, where: PARALLEL_RUNS_WHERE) -> list[tuple[str, Path]]:
    if parallel_yaml_path is not None:
        return [("explicit", Path(parallel_yaml_path).expanduser().resolve())]

    from stackops.utils.accessories import get_repo_root
    from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_STACKOPS_ROOT, LIBRARY_ROOT

    repo_root = get_repo_root(Path.cwd())
    repo_yaml = None if repo_root is None else repo_root.resolve() / _REPO_STACKOPS_DIRECTORY_NAME / _PARALLEL_YAML_FILE_NAME
    private_yaml = DOTFILES_STACKOPS_ROOT / "agents" / "parallel" / _PARALLEL_YAML_FILE_NAME
    public_yaml = CONFIG_ROOT / "agents" / "parallel" / _PARALLEL_YAML_FILE_NAME
    library_yaml = LIBRARY_ROOT / "agents" / "parallel" / _PARALLEL_YAML_FILE_NAME

    match where:
        case "all" | "a":
            paths = [("private", private_yaml), ("public", public_yaml), ("library", library_yaml)]
            if repo_yaml is None:
                return paths
            return [("repo", repo_yaml)] + paths
        case "repo" | "r":
            if repo_yaml is None:
                raise ValueError("--where repo requires running inside a git repository")
            return [("repo", repo_yaml)]
        case "private" | "p":
            return [("private", private_yaml)]
        case "public" | "b":
            return [("public", public_yaml)]
        case "library" | "l":
            return [("library", library_yaml)]


def ensure_parallel_yaml_exists(*, yaml_path: Path) -> bool:
    ensure_stackops_yaml_schema_exists(yaml_path=yaml_path, schema_kind="parallel")
    if yaml_path.exists():
        if not yaml_path.is_file():
            raise ValueError(f"parallel YAML path exists but is not a file: {yaml_path}")
        return False
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(parallel_yaml_template_for_path(yaml_path=yaml_path), encoding="utf-8")
    return True


def parallel_yaml_format_explanation(*, yaml_paths: list[tuple[str, Path]]) -> str:
    formatted_paths = "\n".join(f"- {name}: {path}" for name, path in yaml_paths) if yaml_paths else "- (none)"
    return f"""parallel YAML paths:
{formatted_paths}
Expected format:
{parallel_yaml_template().rstrip()}
"""
