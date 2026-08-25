from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(
            "mcp.json",
            "global",
            context.xdg_config_directory / "stackops/agents/oz/mcp.json",
            "Oz user MCP configuration",
            True,
            is_mcp=True,
        ),
        DoctorPathCandidate(
            "mcp.json", "local", context.project_root / ".warp/mcp.json", "Oz project MCP configuration", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "Oz project guidance", True, is_mcp=False),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.home_directory / ".warp/skills", "Warp-compatible user skill"),
        ("local", context.project_root / ".warp/skills", "Warp-compatible project skill"),
    )
    return collect_standard_resources(
        configurations=configurations, instructions=instructions, instruction_roots=(), skill_roots=skill_roots, plugin_roots=(), plugin_patterns=()
    )


DEFINITION = DoctorAgentDefinition(
    agent="oz",
    display_name="Oz",
    executable="oz",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports the StackOps Oz MCP path and shared guidance resources.",),
)
