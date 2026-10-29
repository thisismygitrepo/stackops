from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import scan_plugin_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots
from stackops.scripts.python.helpers.helpers_agents.maki_paths import resolve_maki_config_directory


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    config_directory = resolve_maki_config_directory(home_dir=context.home_directory)
    roots: tuple[tuple[DoctorOrigin, Path], ...] = (
        ("global", config_directory),
        ("local", context.project_root / ".maki"),
    )
    configurations = tuple(
        DoctorPathCandidate(
            name, origin, root / name, "Maki configuration", name in ("init.lua", "mcp.toml"), is_mcp=name == "mcp.toml",
        )
        for origin, root in roots
        for name in ("init.lua", "mcp.toml", "providers.toml", "permissions.toml", "plugin.toml")
    )
    instructions = [
        DoctorPathCandidate("AGENTS.md", "global", config_directory / "AGENTS.md", "Maki user guidance", False, is_mcp=False),
    ]
    for directory in context.ancestor_directories:
        instruction_paths = (
            directory / name
            for name in (
                "AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md", "COPILOT.md", ".cursorrules",
                ".windsurfrules", ".clinerules", "CONVENTIONS.md", "GEMINI.md", "CODING_AGENT.md",
            )
        )
        instruction_path = next(
            (path for path in instruction_paths if permitted_resource_path(path=path, home_directory=context.home_directory) and path.is_file()),
            directory / "AGENTS.md",
        )
        instructions.extend((
            DoctorPathCandidate(instruction_path.name, "local", instruction_path, "Maki project guidance", True, is_mcp=False),
            DoctorPathCandidate("AGENTS.local.md", "local", directory / "AGENTS.local.md", "Maki local guidance", False, is_mcp=False),
        ))
    skill_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        *shared_skill_roots(context=context),
        ("global", config_directory / "skills", "Maki user skill"),
        ("global", context.home_directory / ".claude/skills", "Maki-scanned Claude user skill"),
        ("global", context.xdg_config_directory / "opencode/skills", "Maki-scanned OpenCode user skill"),
        *(
            ("local", directory / name / "skills", "Maki project skill")
            for directory in context.ancestor_directories
            for name in (".maki", ".claude", ".opencode")
        ),
    )
    resources = collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=(),
        skill_roots=skill_roots,
        plugin_roots=(),
        plugin_patterns=(),
    )
    plugins = scan_plugin_roots(
        roots=tuple((origin, root / "lua", "Maki Lua module; loaded only when required by init.lua") for origin, root in roots),
        patterns=("**/*.lua",),
        state="available",
    )
    return (*resources, *plugins)


DEFINITION = DoctorAgentDefinition(
    agent="maki",
    display_name="Maki",
    executable="maki",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports Maki configuration, project guidance, skills, and Lua modules; executable Lua hooks and custom instruction selection require manual inspection.",),
)
