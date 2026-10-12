from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import scan_plugin_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources
from stackops.scripts.python.helpers.helpers_agents.cortex_paths import resolve_cortex_home


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    home = resolve_cortex_home(home_dir=context.home_directory)
    if not home.is_absolute():
        home = context.working_directory / home
    configurations = (
        DoctorPathCandidate("settings.json", "global", home / "settings.json", "Cortex user settings", True, is_mcp=False),
        DoctorPathCandidate("permissions.json", "global", home / "permissions.json", "Cortex saved permissions", False, is_mcp=False),
        DoctorPathCandidate("mcp.json", "global", home / "mcp.json", "Cortex user MCP servers", True, is_mcp=True),
        DoctorPathCandidate("mcp-disabled.json", "global", home / "mcp-disabled.json", "Cortex disabled MCP servers", False, is_mcp=True),
        DoctorPathCandidate("registry.json", "global", home / "plugins/registry.json", "Cortex managed plugin registry", False, is_mcp=False),
        DoctorPathCandidate(
            "settings.json", "local", context.working_directory / ".cortex/settings.json", "Cortex project settings", True, is_mcp=False,
        ),
        DoctorPathCandidate(
            "mcp.json", "local", context.project_root / ".cortex/mcp.json", "Project MCP servers loaded by StackOps with --mcp-config", False, is_mcp=True,
        ),
    )
    instructions = (
        *(DoctorPathCandidate(name, "global", directory / name, "Cortex user guidance", False, is_mcp=False)
          for directory in (context.home_directory, context.home_directory / ".claude", home.parent, home)
          for name in ("AGENTS.md", "CLAUDE.md", "CORTEX.md", "RULES.md", ".cursorrules")),
        *(DoctorPathCandidate(
            "AGENTS.md", "local", directory / "AGENTS.md", "Cortex project guidance", False, is_mcp=False,
        ) for directory in context.ancestor_directories),
    )
    skill_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("global", home / "skills", "Cortex user skill"),
        ("global", context.home_directory / ".claude/skills", "Claude-compatible user skill"),
        *(("local", context.working_directory / directory / "skills", "Cortex project skill")
          for directory in (".cortex", ".claude", ".agents", ".snova")),
    )
    plugin_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("global", home / "plugins", "Cortex installed plugin; activation is managed by Cortex"),
        ("local", context.working_directory / ".cortex/plugins", "Cortex project plugin"),
        ("local", context.working_directory / ".claude/plugins", "Claude-compatible project plugin"),
    )
    return (
        *collect_standard_resources(
            configurations=configurations,
            instructions=instructions,
            instruction_roots=(),
            skill_roots=skill_roots,
            plugin_roots=(),
            plugin_patterns=(),
        ),
        *scan_plugin_roots(
            roots=plugin_roots,
            patterns=("**/.cortex-plugin/plugin.json", "**/.claude-plugin/plugin.json"),
            state="available",
        ),
    )


DEFINITION = DoctorAgentDefinition(
    agent="cortex",
    display_name="Snowflake Cortex Code",
    executable="cortex",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=(
        "SNOWFLAKE_HOME is honored. Project MCP configuration is loaded explicitly by StackOps.",
        "Reports local configuration and plugin manifests. Profile resources, plugin activation and organization policies require inspection in Cortex.",
    ),
)
