from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources, shared_skill_roots


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    configurations = (
        DoctorPathCandidate(
            "settings.json", "global", context.xdg_config_directory / "muse/settings.json", "Muse user settings", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "Muse project guidance", True, is_mcp=False),
        DoctorPathCandidate("CLAUDE.md", "local", context.project_root / "CLAUDE.md", "Muse fallback project guidance", False, is_mcp=False),
    )
    skill_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        *shared_skill_roots(context=context),
        ("global", context.xdg_config_directory / "muse/skills", "Muse user skill"),
        ("local", context.project_root / ".claude/skills", "Muse-scanned Claude project skill"),
        ("local", context.project_root / ".codex/skills", "Muse-scanned Codex project skill"),
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
    agent="muse",
    display_name="Muse Code",
    executable="muse",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Reports Muse user settings, project guidance, and skill roots; plugin bundles and project hooks are not inspected.",),
)
