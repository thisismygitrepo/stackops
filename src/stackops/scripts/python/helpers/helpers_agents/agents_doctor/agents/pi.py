from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi_context import collect_pi_context_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.pi_settings import collect_pi_settings_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource


def collect_resources(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    return (*collect_pi_settings_resources(context), *collect_pi_context_resources(context))


DEFINITION = DoctorAgentDefinition(
    agent="pi",
    display_name="Pi",
    executable="pi",
    version_arguments=("--version",),
    support_level="focused",
    collector=collect_resources,
    notes=(
        "Pi's plugin equivalents are executable extensions and Pi packages.",
        "Pi core has no built-in MCP support; .pi/mcp.json is consumed only by an installed extension.",
    ),
)
