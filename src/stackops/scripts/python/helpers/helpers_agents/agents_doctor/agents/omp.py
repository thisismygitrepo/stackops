from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config import config_entries, configuration_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_context import instructions, skills
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugins import configured_extensions, plugins
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    entries = config_entries(context=context)
    extension_declarations = configured_extensions(config_entries=entries)
    return (
        *configuration_resources(config_entries=entries),
        *plugins(context=context, configured_extensions=extension_declarations),
        *skills(context=context, config_entries=entries, configured_extensions=extension_declarations),
        *instructions(context=context),
    )


DEFINITION = DoctorAgentDefinition(
    agent="omp",
    display_name="Oh My Pi",
    executable="omp",
    version_arguments=("--version",),
    support_level="focused",
    collector=collect,
    notes=("Global resources follow the active OMP profile through its agent directory.",),
)
