from dataclasses import dataclass
from typing import cast, get_args

from stackops.scripts.python.helpers.helpers_webui.constants import EVERY_ITEM_CHOICE, KeywordChoiceSource


# The fields mean what they do in `FieldChoices`.
@dataclass(frozen=True, slots=True)
class KeywordChoices:
    choices: tuple[str, ...]
    default: str | None
    separator: str
    whole: str


# Each set is read from where its command keeps it, so a keyword added there shows up here. The imports are inside: they are only needed once a
# form with such a field opens, and the agent registry is not small.
def read_keyword_choices(source: KeywordChoiceSource) -> KeywordChoices:
    match source:
        case "config_agents":
            from stackops.utils.schemas.fire_agents.fire_agents_types import CONFIG_AGENT_VALUES

            return KeywordChoices(choices=(EVERY_ITEM_CHOICE, *CONFIG_AGENT_VALUES), default=None, separator=",", whole=EVERY_ITEM_CHOICE)
        case "mcp_agents":
            from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

            return KeywordChoices(choices=cast(tuple[str, ...], get_args(AGENTS)), default=None, separator=",", whole="")
        case "doctor_agent":
            from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_DEFINITION_BY_AGENT

            return KeywordChoices(choices=(EVERY_ITEM_CHOICE, *DOCTOR_DEFINITION_BY_AGENT), default=None, separator="", whole="")
        case "doctor_resources":
            from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorResourceFocus

            return KeywordChoices(choices=cast(tuple[str, ...], get_args(DoctorResourceFocus)), default=None, separator=",", whole=EVERY_ITEM_CHOICE)
        case "reset_resources":
            from stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants import CLEANUP_RESOURCE_CHOICES

            return KeywordChoices(choices=CLEANUP_RESOURCE_CHOICES, default=None, separator=",", whole=EVERY_ITEM_CHOICE)
        case "agent_states":
            from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentStatus

            return KeywordChoices(choices=cast(tuple[str, ...], get_args(AgentStatus)), default=None, separator="", whole="")
        # Left alone, the command runs every tool, so that is what an untouched field shows as picked.
        case "type_check_tools":
            from stackops.scripts.python.ai.scripts.constants import TYPE_CHECK_TOOL_NAMES

            return KeywordChoices(choices=TYPE_CHECK_TOOL_NAMES, default=",".join(TYPE_CHECK_TOOL_NAMES), separator=",", whole="")
