from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(
            "settings.json", "global", context.home_directory / ".qwen/settings.json", "Qwen user settings", True, is_mcp=True
        ),
        DoctorPathCandidate(
            "settings.json", "local", context.project_root / ".qwen/settings.json", "Qwen project settings", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate(
            "QWEN.md", "global", context.home_directory / ".qwen/QWEN.md", "inherited Qwen user guidance", False, is_mcp=False
        ),
        DoctorPathCandidate("QWEN.md", "local", context.project_root / "QWEN.md", "Qwen project guidance", True, is_mcp=False),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.home_directory / ".qwen/skills", "Qwen user skill"),
        ("local", context.project_root / ".qwen/skills", "Qwen project skill"),
    )
    plugin_roots = (
        ("global", context.home_directory / ".qwen/extensions", "Qwen user extension"),
        ("local", context.project_root / ".qwen/extensions", "Qwen project extension"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=(),
        skill_roots=skill_roots,
        plugin_roots=plugin_roots,
        plugin_patterns=("**/package.json", "**/qwen-extension.json"),
    )


DEFINITION = DoctorAgentDefinition(
    agent="qwen",
    display_name="Qwen Code",
    executable="qwen",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports Qwen settings, guidance, extensions, and compatible skills.",),
)
