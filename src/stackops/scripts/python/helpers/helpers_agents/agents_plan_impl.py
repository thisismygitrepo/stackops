import json
import re
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast, get_args

from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import run as run_agent_prompt
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.utils.schemas.yaml_schema import JsonObject


type PlanPhaseStatus = Literal["pending", "ready", "running", "blocked", "completed", "skipped", "cancelled"]
type AgentOpsCommand = Literal["handover", "iter", "parallel-agents", "parallel-isolated-agents"]

PlanPathPair: TypeAlias = tuple[Path, Path]

PLAN_DIRECTORY: Final[Path] = Path(".ai") / "plans"
PLAN_SCHEMA_FILENAME: Final[str] = "plan.schema.json"
PLAN_SCHEMA_VERSION: Final[int] = 1
_PLAN_SLUG_MAX_LENGTH: Final[int] = 64
_AGENT_VALUES: Final[tuple[AGENTS, ...]] = cast(tuple[AGENTS, ...], get_args(AGENTS))
_PLAN_PHASE_STATUSES: Final[tuple[PlanPhaseStatus, ...]] = (
    "pending",
    "ready",
    "running",
    "blocked",
    "completed",
    "skipped",
    "cancelled",
)
_AGENTOPS_COMMANDS: Final[tuple[AgentOpsCommand, ...]] = ("handover", "iter", "parallel-agents", "parallel-isolated-agents")


def derive_plan_slug(*, user_prompt: str) -> str:
    lowered = user_prompt.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if slug == "":
        raise ValueError("Plan prompt must contain at least one ASCII letter or digit")
    return slug[:_PLAN_SLUG_MAX_LENGTH].rstrip("-")


def resolve_plan_paths(*, user_prompt: str, cwd: Path) -> PlanPathPair:
    plan_directory = cwd / PLAN_DIRECTORY
    slug = derive_plan_slug(user_prompt=user_prompt)
    return plan_directory / f"{slug}.plan.json", plan_directory / PLAN_SCHEMA_FILENAME


def plan_json_schema() -> JsonObject:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "StackOps agent execution plan",
        "description": "A phased plan for coordinating StackOps agents and agentops workflows.",
        "type": "object",
        "additionalProperties": False,
        "required": ["$schema", "schemaVersion", "slug", "objective", "phases"],
        "properties": {
            "$schema": {"const": f"./{PLAN_SCHEMA_FILENAME}"},
            "schemaVersion": {"const": PLAN_SCHEMA_VERSION},
            "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$"},
            "objective": {"type": "string", "minLength": 1},
            "phases": {"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/phase"}},
        },
        "definitions": {
            "phase": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "status", "agent", "agentOps", "task"],
                "properties": {
                    "id": {"type": "string", "pattern": "^phase-[0-9]{3}$"},
                    "title": {"type": "string", "minLength": 1},
                    "status": {"enum": list(_PLAN_PHASE_STATUSES)},
                    "agent": {"enum": list(_AGENT_VALUES)},
                    "agentOps": {"enum": [*_AGENTOPS_COMMANDS, None]},
                    "task": {"type": "string", "minLength": 1},
                },
            }
        },
    }


def write_plan_schema(*, schema_path: Path, schema: JsonObject) -> None:
    if schema_path.exists() and not schema_path.is_file():
        raise ValueError(f"Plan schema path exists but is not a file: {schema_path}")
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_plan_prompt(*, user_prompt: str, plan_path: Path, schema_path: Path, schema: JsonObject) -> str:
    slug = plan_path.name.removesuffix(".plan.json")
    agent_values = ", ".join(_AGENT_VALUES)
    agentops_commands = ", ".join(_AGENTOPS_COMMANDS)
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    return f"""You are creating a StackOps execution plan JSON file.

User objective:
{user_prompt}

Write the final plan to:
{plan_path}

The schema has already been written to:
{schema_path}

The plan JSON must be named `{plan_path.name}` and must contain `$schema: "./{PLAN_SCHEMA_FILENAME}"`.
Do not execute the plan. Do not edit project files other than the target plan JSON. Inspect the repository only as needed to produce a realistic plan.

Use this exact JSON Schema:
```json
{schema_json}
```

Planning rules:
- Use slug `{slug}` in the top-level `slug` field.
- Use schemaVersion `{PLAN_SCHEMA_VERSION}`.
- Phases are ordered. Each phase depends on the previous phases, so do not add dependency fields.
- `status` is a string enum, not a boolean. Initial phases should usually be `pending`; use `completed`, `blocked`, or `skipped` only for facts already true.
- Every `agent` must be one of: {agent_values}.
- `agentOps` must be one of: {agentops_commands}, or JSON null for a simple direct agent prompt.
- Use `iter` for unbounded or repeated quality improvement.
- Use `parallel-agents` when multiple Herdr-managed agents can work on independent slices in the same worktree.
- Use `parallel-isolated-agents` when agents need isolated wt/Worktrunk worktrees to avoid edit collisions.
- Use `handover` only when the phase is explicitly transferring active work to another interactive agent.
- For workflows that need parallel exploration and then integration, make separate phases: one parallel agentops phase, then a direct synthesis phase with `agentOps: null`.
- Do not invent operation names such as `iter-parallel`; express combinations through multiple phases.
- For every non-null `agentOps`, `task` must start exactly with: `Using skill agentops, <agentOps>, work towards`.
- For `agentOps: null`, write a direct single-agent task and do not start it with `Using skill agentops`.
- Each task must be self-contained enough for an agent that cannot see this conversation, including validation, expected artifacts, and handoff conditions.
- Make the smallest plan that can plausibly complete the objective; avoid speculative phases.
"""


def run_plan(*, user_prompt: str, agent: AGENTS) -> None:
    plan_path, schema_path = resolve_plan_paths(user_prompt=user_prompt, cwd=Path.cwd())
    schema = plan_json_schema()
    write_plan_schema(schema_path=schema_path, schema=schema)
    prompt = build_plan_prompt(user_prompt=user_prompt, plan_path=plan_path, schema_path=schema_path, schema=schema)
    run_agent_prompt(
        prompt=prompt,
        agent=agent,
        reasoning_effort=None,
        context="",
        context_path=None,
        prompts_yaml_path=None,
        context_name=None,
        source="all",
        edit=False,
        show_prompts_yaml_format=False,
    )
