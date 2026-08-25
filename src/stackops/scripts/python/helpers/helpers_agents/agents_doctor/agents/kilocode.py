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
            "mcp.json",
            "global",
            context.xdg_config_directory / "kilocode/mcp.json",
            "Kilo Code user MCP configuration",
            True,
            is_mcp=True,
        ),
        DoctorPathCandidate(
            "mcp.json", "local", context.project_root / ".kilocode/mcp.json", "Kilo Code project MCP configuration", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "shared project guidance", False, is_mcp=False),
    )
    instruction_roots = (DoctorFileRoot("local", context.project_root / ".kilocode/rules", ("**/*.md",), "Kilo Code project rule"),)
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.xdg_config_directory / "kilocode/skills", "Kilo Code user skill"),
        ("local", context.project_root / ".kilocode/skills", "Kilo Code project skill"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=instruction_roots,
        skill_roots=skill_roots,
        plugin_roots=(),
        plugin_patterns=(),
    )


DEFINITION = DoctorAgentDefinition(
    agent="kilocode",
    display_name="Kilo Code",
    executable="kilocode",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Kilo Code rules and shared skills are reported independently.",),
)
