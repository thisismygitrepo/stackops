from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources
from stackops.scripts.python.helpers.helpers_agents.prime_agent_paths import resolve_prime_agent_directory


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    agent_directory = resolve_prime_agent_directory(home_dir=context.home_directory)
    configurations = (
        DoctorPathCandidate("settings.json", "global", agent_directory / "settings.json", "prime-agent user settings", True, is_mcp=True),
        DoctorPathCandidate(
            "settings.json", "local", context.project_root / ".prime/agent/settings.json",
            "prime-agent project settings; mcpServers here are ignored", False, is_mcp=False,
        ),
    )
    instruction_directories: tuple[tuple[DoctorOrigin, Path, str, bool], ...] = (
        ("global", agent_directory, "prime-agent user guidance", False),
        *(("local", directory, "prime-agent project guidance", True) for directory in context.ancestor_directories),
    )
    instructions: list[DoctorPathCandidate] = []
    for origin, directory, detail, include_missing in instruction_directories:
        instruction_path = next(
            (
                directory / name
                for name in ("AGENTS.md", "AGENTS.MD", "CLAUDE.md", "CLAUDE.MD")
                if permitted_resource_path(path=directory / name, home_directory=context.home_directory) and (directory / name).is_file()
            ),
            directory / "AGENTS.md",
        )
        instructions.append(DoctorPathCandidate(instruction_path.name, origin, instruction_path, detail, include_missing, is_mcp=False))
    skill_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("global", agent_directory / "skills", "prime-agent user skill"),
        ("local", context.project_root / ".prime/agent/skills", "prime-agent project skill"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=(),
        skill_roots=skill_roots,
        plugin_roots=(),
        plugin_patterns=(),
    )


DEFINITION = DoctorAgentDefinition(
    agent="prime-agent",
    display_name="Prime Agent",
    executable="prime-agent",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports prime-agent settings, AGENTS.md/CLAUDE.md guidance, and skills; only user settings can declare MCP servers.",),
)
