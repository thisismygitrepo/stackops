from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import (
    DoctorFileRoot,
    DoctorPathCandidate,
    collect_standard_resources,
    shared_skill_roots,
)


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate("settings.json", "global", context.claude_home / "settings.json", "Claude user settings", True),
        DoctorPathCandidate(".claude.json", "global", context.home_directory / ".claude.json", "Claude user MCP and state configuration", True),
        DoctorPathCandidate("settings.json", "local", context.project_root / ".claude/settings.json", "Claude shared project settings", True),
        DoctorPathCandidate(
            "settings.local.json", "local", context.project_root / ".claude/settings.local.json", "Claude private project settings", True
        ),
        DoctorPathCandidate(".mcp.json", "local", context.project_root / ".mcp.json", "Claude project MCP configuration", True),
    )
    instructions = (
        DoctorPathCandidate("CLAUDE.md", "global", context.claude_home / "CLAUDE.md", "inherited Claude user guidance", True),
        DoctorPathCandidate("CLAUDE.md", "local", context.project_root / "CLAUDE.md", "Claude project guidance", True),
        DoctorPathCandidate("CLAUDE.local.md", "local", context.project_root / "CLAUDE.local.md", "private Claude project guidance", False),
    )
    instruction_roots = (
        DoctorFileRoot("global", context.claude_home / "rules", ("**/*.md",), "Claude user rule"),
        DoctorFileRoot("local", context.project_root / ".claude/rules", ("**/*.md",), "Claude project rule"),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.claude_home / "skills", "Claude user skill"),
        ("local", context.project_root / ".claude/skills", "Claude project skill"),
    )
    plugin_roots = (
        ("global", context.claude_home / "plugins", "Claude user plugin"),
        ("local", context.project_root / ".claude/plugins", "Claude project plugin"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=instruction_roots,
        skill_roots=skill_roots,
        plugin_roots=plugin_roots,
        plugin_patterns=("**/.claude-plugin/plugin.json", "**/plugin.json", "**/package.json"),
    )


DEFINITION = DoctorAgentDefinition(
    agent="claude",
    display_name="Claude Code",
    executable="claude",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("User and project settings, rules, skills, and plugin manifests are reported.",),
)
