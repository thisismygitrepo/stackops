import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import (
    DoctorFileRoot,
    DoctorPathCandidate,
    collect_standard_resources,
    shared_skill_roots,
)


def _cursor_config_root(*, context: DoctorContext) -> Path:
    configured_root = os.environ.get("CURSOR_CONFIG_DIR")
    if configured_root is not None and configured_root.strip() != "":
        return Path(configured_root).expanduser().resolve(strict=False)
    xdg_config_root = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_root is not None and xdg_config_root.strip() != "":
        return context.xdg_config_directory / "cursor"
    return context.home_directory / ".cursor"


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    cursor_config_root = _cursor_config_root(context=context)
    configurations = (
        DoctorPathCandidate("cli-config.json", "global", cursor_config_root / "cli-config.json", "Cursor CLI user configuration", True),
        DoctorPathCandidate("mcp.json", "global", cursor_config_root / "mcp.json", "Cursor user MCP configuration", True),
        DoctorPathCandidate("cli.json", "local", context.project_root / ".cursor/cli.json", "Cursor project CLI permissions", True),
        DoctorPathCandidate("mcp.json", "local", context.project_root / ".cursor/mcp.json", "Cursor project MCP configuration", True),
    )
    instructions = (
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "project agent guidance", True),
        DoctorPathCandidate("CLAUDE.md", "local", context.project_root / "CLAUDE.md", "Claude-compatible project guidance", False),
    )
    instruction_roots = (
        DoctorFileRoot("local", context.project_root / ".cursor/rules", ("*.md", "*.mdc", "**/*.md", "**/*.mdc"), "Cursor project rule"),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", cursor_config_root / "skills", "Cursor user skill"),
        ("local", context.project_root / ".cursor/skills", "Cursor project skill"),
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
    agent="cursor-agent",
    display_name="Cursor Agent",
    executable="cursor-agent",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Cursor rules and shared Agent Skills are shown separately.",),
)
