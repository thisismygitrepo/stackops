from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_config import config_layers, config_resources, effective_fallback_names
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_context import instruction_resources, skill_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugin_cache import cached_plugins
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugins import plugin_setting_resources, plugin_settings
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource


def collect_codex_resources(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    layers = config_layers(context=context)
    settings = plugin_settings(layers=layers)
    setting_resources, effective_settings = plugin_setting_resources(settings=settings)
    cached_plugin_resources, plugin_skills = cached_plugins(context=context, effective_settings=effective_settings)
    fallback_names = effective_fallback_names(layers=layers)
    return (
        *config_resources(layers=layers),
        *instruction_resources(context=context, fallback_names=fallback_names),
        *setting_resources,
        *cached_plugin_resources,
        *skill_resources(context=context),
        *plugin_skills,
    )


DEFINITION: Final[DoctorAgentDefinition] = DoctorAgentDefinition(
    agent="codex",
    display_name="Codex",
    executable="codex",
    version_arguments=("--version",),
    support_level="focused",
    collector=collect_codex_resources,
    notes=(
        "Project config and instruction activity assumes Codex trusts the project.",
        "Instruction selection models filename precedence; project_doc_max_bytes may truncate the combined project guidance.",
        "Skills are reported as available because Codex reads a skill body only when the skill is selected.",
        "A cached plugin manifest is available, not enabled, unless the effective [plugins.*] entry enables it.",
    ),
)
