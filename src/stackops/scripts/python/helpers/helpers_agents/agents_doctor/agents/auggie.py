from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(
            "settings.json", "global", context.home_directory / ".augment/settings.json", "Auggie user settings", True, is_mcp=True
        ),
        DoctorPathCandidate(
            "settings.json", "local", context.project_root / ".augment/settings.json", "Auggie project settings", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate(
            "guidelines.md", "global", context.home_directory / ".augment/guidelines.md", "inherited Auggie guidance", False, is_mcp=False
        ),
        DoctorPathCandidate(
            "guidelines.md", "local", context.project_root / ".augment/guidelines.md", "Auggie project guidance", True, is_mcp=False
        ),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.home_directory / ".augment/skills", "Auggie user skill"),
        ("local", context.project_root / ".augment/skills", "Auggie project skill"),
    )
    return collect_standard_resources(
        configurations=configurations, instructions=instructions, instruction_roots=(), skill_roots=skill_roots, plugin_roots=(), plugin_patterns=()
    )


DEFINITION = DoctorAgentDefinition(
    agent="auggie",
    display_name="Auggie",
    executable="auggie",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Auggie guidelines are shown as inherited or project-local guidance.",),
)
