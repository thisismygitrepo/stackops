import json
from pathlib import Path
from typing import Final, TypedDict, cast, get_args

from stackops.scripts.python.helpers.helpers_agents.agents_plan_impl import AgentOpsCommand, PlanPhaseStatus
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


class PlanPhase(TypedDict):
    id: str
    title: str
    status: PlanPhaseStatus
    agent: AGENTS
    agentOps: AgentOpsCommand | None
    task: str


class PlanDocument(TypedDict):
    schema_ref: str
    schemaVersion: int
    slug: str
    objective: str
    phases: list[PlanPhase]


READY_STATUSES: Final[frozenset[PlanPhaseStatus]] = frozenset({"pending", "ready"})
ADVANCE_STATUSES: Final[frozenset[PlanPhaseStatus]] = frozenset({"completed", "skipped"})
_STATUS_VALUES: Final[tuple[PlanPhaseStatus, ...]] = ("pending", "ready", "running", "blocked", "completed", "skipped", "cancelled")
_AGENT_VALUES: Final[tuple[AGENTS, ...]] = cast(tuple[AGENTS, ...], get_args(AGENTS))
_AGENTOPS_COMMANDS: Final[tuple[AgentOpsCommand, ...]] = ("handover", "iter", "parallel-agents", "parallel-isolated-agents")


def read_plan_document(*, plan_path: Path) -> PlanDocument:
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    root = _required_mapping(value=raw, label="plan")
    phases_value = root.get("phases")
    if not isinstance(phases_value, list):
        raise ValueError("plan.phases must be an array")
    phases = [_parse_phase(value=phase_value, index=index) for index, phase_value in enumerate(phases_value)]
    return {
        "schema_ref": _required_string(mapping=root, key="$schema", label="plan"),
        "schemaVersion": _required_int(mapping=root, key="schemaVersion", label="plan"),
        "slug": _required_string(mapping=root, key="slug", label="plan"),
        "objective": _required_string(mapping=root, key="objective", label="plan"),
        "phases": phases,
    }


def write_plan_document(*, plan_path: Path, plan: PlanDocument) -> None:
    payload = {
        "$schema": plan["schema_ref"],
        "schemaVersion": plan["schemaVersion"],
        "slug": plan["slug"],
        "objective": plan["objective"],
        "phases": plan["phases"],
    }
    plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_phase(*, value: object, index: int) -> PlanPhase:
    phase = _required_mapping(value=value, label=f"plan.phases[{index}]")
    return {
        "id": _required_string(mapping=phase, key="id", label=f"plan.phases[{index}]"),
        "title": _required_string(mapping=phase, key="title", label=f"plan.phases[{index}]"),
        "status": _required_status(mapping=phase, key="status", label=f"plan.phases[{index}]"),
        "agent": _required_agent(mapping=phase, key="agent", label=f"plan.phases[{index}]"),
        "agentOps": _optional_agentops(mapping=phase, key="agentOps", label=f"plan.phases[{index}]"),
        "task": _required_string(mapping=phase, key="task", label=f"plan.phases[{index}]"),
    }


def _required_mapping(*, value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _required_string(*, mapping: dict[str, object], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value


def _required_int(*, mapping: dict[str, object], key: str, label: str) -> int:
    value = mapping.get(key)
    if type(value) is not int:
        raise ValueError(f"{label}.{key} must be an integer")
    return value


def _required_status(*, mapping: dict[str, object], key: str, label: str) -> PlanPhaseStatus:
    value = _required_string(mapping=mapping, key=key, label=label)
    if value not in _STATUS_VALUES:
        raise ValueError(f"{label}.{key} must be one of: {', '.join(_STATUS_VALUES)}")
    return value


def _required_agent(*, mapping: dict[str, object], key: str, label: str) -> AGENTS:
    value = _required_string(mapping=mapping, key=key, label=label)
    if value not in _AGENT_VALUES:
        raise ValueError(f"{label}.{key} must be one of: {', '.join(_AGENT_VALUES)}")
    return value


def _optional_agentops(*, mapping: dict[str, object], key: str, label: str) -> AgentOpsCommand | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value not in _AGENTOPS_COMMANDS:
        raise ValueError(f"{label}.{key} must be null or one of: {', '.join(_AGENTOPS_COMMANDS)}")
    return value
