from typing import Final, cast, get_args

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.amazon_q import DEFINITION as AMAZON_Q
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.agy import DEFINITION as AGY
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.auggie import DEFINITION as AUGGIE
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.claude import DEFINITION as CLAUDE
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cline import DEFINITION as CLINE
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex import DEFINITION as CODEX
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.copilot import DEFINITION as COPILOT
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.crush import DEFINITION as CRUSH
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.cursor_agent import DEFINITION as CURSOR_AGENT
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.droid import DEFINITION as DROID
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.forge import DEFINITION as FORGE
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.kilocode import DEFINITION as KILOCODE
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp import DEFINITION as OMP
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode import DEFINITION as OPENCODE
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.oz import DEFINITION as OZ
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi import DEFINITION as PI
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.qwen import DEFINITION as QWEN
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorAgentDefinition
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


DOCTOR_AGENT_DEFINITIONS: Final[tuple[DoctorAgentDefinition, ...]] = (
    CODEX,
    PI,
    OMP,
    OPENCODE,
    AGY,
    CURSOR_AGENT,
    CLAUDE,
    QWEN,
    COPILOT,
    FORGE,
    CRUSH,
    AMAZON_Q,
    KILOCODE,
    CLINE,
    AUGGIE,
    OZ,
    DROID,
)
DOCTOR_DEFINITION_BY_AGENT: Final[dict[DoctorAgent, DoctorAgentDefinition]] = {
    definition.agent: definition for definition in DOCTOR_AGENT_DEFINITIONS
}
DOCTOR_AGENT_ALIASES: Final[dict[str, DoctorAgent]] = {
    "antigravity": "agy",
    "amazon-q": "q",
    "augment": "auggie",
    "claude-code": "claude",
    "cursor": "cursor-agent",
    "factory-droid": "droid",
    "github-copilot": "copilot",
    "kilo": "kilocode",
    "oh-my-pi": "omp",
    "qwen-code": "qwen",
}
_EXPECTED_DOCTOR_AGENTS: Final[frozenset[DoctorAgent]] = frozenset((*cast(tuple[DoctorAgent, ...], get_args(AGENTS)), "omp"))

if len(DOCTOR_DEFINITION_BY_AGENT) != len(DOCTOR_AGENT_DEFINITIONS):
    raise RuntimeError("Duplicate agent target in doctor registry")
if frozenset(DOCTOR_DEFINITION_BY_AGENT) != _EXPECTED_DOCTOR_AGENTS:
    missing_agents = sorted(_EXPECTED_DOCTOR_AGENTS.difference(DOCTOR_DEFINITION_BY_AGENT))
    unexpected_agents = sorted(frozenset(DOCTOR_DEFINITION_BY_AGENT).difference(_EXPECTED_DOCTOR_AGENTS))
    raise RuntimeError(f"Incomplete doctor registry: missing={missing_agents}, unexpected={unexpected_agents}")


def resolve_doctor_definitions(*, requested_agent: str) -> tuple[DoctorAgentDefinition, ...]:
    normalized_agent = requested_agent.strip().casefold()
    if normalized_agent == "all":
        return DOCTOR_AGENT_DEFINITIONS
    canonical_agent = cast(DoctorAgent, DOCTOR_AGENT_ALIASES.get(normalized_agent, normalized_agent))
    definition = DOCTOR_DEFINITION_BY_AGENT.get(canonical_agent)
    if definition is not None:
        return (definition,)
    supported = ", ".join((*DOCTOR_DEFINITION_BY_AGENT, *DOCTOR_AGENT_ALIASES))
    raise ValueError(f"Unsupported doctor target: {requested_agent}. Supported targets: all, {supported}")
