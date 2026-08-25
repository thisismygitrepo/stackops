from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import (
    DoctorFileRoot,
    DoctorPathCandidate,
    collect_standard_resources,
    shared_skill_roots,
)


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    settings_suffix = ".cline/data/settings/cline_mcp_settings.json"
    configurations = (
        DoctorPathCandidate("cline_mcp_settings.json", "global", context.home_directory / settings_suffix, "Cline user MCP configuration", True),
        DoctorPathCandidate("cline_mcp_settings.json", "local", context.project_root / settings_suffix, "Cline project MCP configuration", True),
    )
    instruction_roots = (DoctorFileRoot("local", context.project_root / ".clinerules", ("*.md", "**/*.md"), "Cline project rule"),)
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.home_directory / ".cline/skills", "Cline user skill"),
        ("local", context.project_root / ".cline/skills", "Cline project skill"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=(),
        instruction_roots=instruction_roots,
        skill_roots=skill_roots,
        plugin_roots=(),
        plugin_patterns=(),
    )


DEFINITION = DoctorAgentDefinition(
    agent="cline",
    display_name="Cline",
    executable="cline",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Cline rules and skill directories are surfaced with their scope.",),
)
