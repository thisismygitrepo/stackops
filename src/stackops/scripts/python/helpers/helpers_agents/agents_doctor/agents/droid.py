from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate("settings.json", "global", context.home_directory / ".factory/settings.json", "Droid user settings", True),
        DoctorPathCandidate("settings.json", "local", context.project_root / ".factory/settings.json", "Droid project settings", True),
    )
    instructions = (
        DoctorPathCandidate("DROID.md", "global", context.home_directory / ".factory/DROID.md", "inherited Droid guidance", False),
        DoctorPathCandidate("DROID.md", "local", context.project_root / "DROID.md", "Droid project guidance", True),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.home_directory / ".factory/skills", "Droid user skill"),
        ("local", context.project_root / ".factory/skills", "Droid project skill"),
    )
    plugin_roots = (
        ("global", context.home_directory / ".factory/plugins", "Droid user plugin"),
        ("local", context.project_root / ".factory/plugins", "Droid project plugin"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=(),
        skill_roots=skill_roots,
        plugin_roots=plugin_roots,
        plugin_patterns=("**/plugin.json", "**/package.json"),
    )


DEFINITION = DoctorAgentDefinition(
    agent="droid",
    display_name="Factory Droid",
    executable="droid",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports Factory settings, guidance, skills, and plugin manifests.",),
)
