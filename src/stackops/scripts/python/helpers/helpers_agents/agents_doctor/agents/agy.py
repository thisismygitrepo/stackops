from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(
            "mcp_config.json",
            "global",
            context.home_directory / ".gemini/antigravity-cli/mcp_config.json",
            "Antigravity user MCP configuration",
            True,
            is_mcp=True,
        ),
        DoctorPathCandidate(
            "mcp_config.json",
            "local",
            context.project_root / ".agents/mcp_config.json",
            "Antigravity project MCP configuration",
            True,
            is_mcp=True,
        ),
    )
    instructions = (
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "project agent guidance", True, is_mcp=False),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.home_directory / ".gemini/skills", "Gemini-compatible user skill"),
        ("local", context.project_root / ".gemini/skills", "Gemini-compatible project skill"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=(),
        skill_roots=skill_roots,
        plugin_roots=(("global", context.home_directory / ".gemini/extensions", "Gemini-compatible extension"),),
        plugin_patterns=("**/package.json", "**/gemini-extension.json"),
    )


DEFINITION = DoctorAgentDefinition(
    agent="agy",
    display_name="Antigravity",
    executable="agy",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports StackOps-managed paths and compatible shared resources.",),
)
