from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(".mcp.json", "global", context.home_directory / "forge/.mcp.json", "Forge user MCP configuration", True),
        DoctorPathCandidate("forge.yaml", "local", context.project_root / "forge.yaml", "Forge project configuration", True),
        DoctorPathCandidate(".mcp.json", "local", context.project_root / ".mcp.json", "Forge project MCP configuration", True),
    )
    instructions = (DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "Forge project guidance", True),)
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=(),
        skill_roots=shared_skill_roots(context=context),
        plugin_roots=(),
        plugin_patterns=(),
    )


DEFINITION = DoctorAgentDefinition(
    agent="forge",
    display_name="Forge",
    executable="forge",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports StackOps-managed Forge configuration and shared skills.",),
)
