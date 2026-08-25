import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def _global_config_paths(*, context: DoctorContext) -> tuple[Path, ...]:
    configured_path = os.environ.get("CRUSH_GLOBAL_CONFIG")
    if configured_path is not None and configured_path.strip() != "":
        return (Path(configured_path).expanduser().resolve(strict=False),)
    global_config_root = context.xdg_config_directory / "crush"
    return global_config_root / "crushrc", global_config_root / "crush.json"


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    global_config_paths = _global_config_paths(context=context)
    global_config_root = global_config_paths[0].parent
    configurations = (
        *(DoctorPathCandidate(path.name, "global", path, "Crush user configuration", True, is_mcp=True) for path in global_config_paths),
        DoctorPathCandidate(
            ".crush.json", "local", context.project_root / ".crush.json", "Crush project configuration", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate("CRUSH.md", "global", global_config_root / "CRUSH.md", "inherited Crush user guidance", False, is_mcp=False),
        DoctorPathCandidate(
            "AGENTS.md", "global", context.xdg_config_directory / "AGENTS.md", "inherited shared user guidance", False, is_mcp=False
        ),
        DoctorPathCandidate("CRUSH.md", "local", context.project_root / "CRUSH.md", "Crush project guidance", True, is_mcp=False),
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "shared project guidance", False, is_mcp=False),
    )
    configured_skill_root = os.environ.get("CRUSH_SKILLS_DIR")
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", context.xdg_config_directory / "agents/skills", "XDG shared user skill"),
        ("global", global_config_root / "skills", "Crush user skill"),
        ("global", context.claude_home / "skills", "Claude-compatible user skill"),
        ("local", context.project_root / ".crush/skills", "Crush project skill"),
        ("local", context.project_root / ".claude/skills", "Claude-compatible project skill"),
        ("local", context.project_root / ".cursor/skills", "Cursor-compatible project skill"),
        *(
            (("global", Path(configured_skill_root).expanduser().resolve(strict=False), "CRUSH_SKILLS_DIR"),)
            if configured_skill_root is not None and configured_skill_root.strip() != ""
            else ()
        ),
    )
    return collect_standard_resources(
        configurations=configurations, instructions=instructions, instruction_roots=(), skill_roots=skill_roots, plugin_roots=(), plugin_patterns=()
    )


DEFINITION = DoctorAgentDefinition(
    agent="crush",
    display_name="Crush",
    executable="crush",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Crush extends itself through Agent Skills; it has no separate plugin directory.",),
)
