from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import (
    DoctorFileRoot,
    DoctorPathCandidate,
    collect_standard_resources,
    shared_skill_roots,
)


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(
            "settings.json", "global", context.xdg_config_directory / "amazon-q/settings.json", "Amazon Q user settings", True, is_mcp=True
        ),
        DoctorPathCandidate(
            "settings.json", "local", context.project_root / ".amazonq/settings.json", "Amazon Q project settings", True, is_mcp=True
        ),
    )
    instruction_roots = (
        DoctorFileRoot("global", context.xdg_config_directory / "amazon-q/rules", ("**/*.md",), "Amazon Q user rule"),
        DoctorFileRoot("local", context.project_root / ".amazonq/rules", ("**/*.md",), "Amazon Q project rule"),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.xdg_config_directory / "amazon-q/skills", "Amazon Q user skill"),
        ("local", context.project_root / ".amazonq/skills", "Amazon Q project skill"),
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
    agent="q",
    display_name="Amazon Q Developer",
    executable="q",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Amazon Q rule files are reported as instruction resources.",),
)
