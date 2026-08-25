import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import (
    DoctorFileRoot,
    DoctorPathCandidate,
    collect_standard_resources,
    shared_skill_roots,
)


def _copilot_home(*, context: DoctorContext) -> Path:
    configured_home = os.environ.get("COPILOT_HOME")
    if configured_home is None or configured_home.strip() == "":
        return context.home_directory / ".copilot"
    return Path(configured_home).expanduser().resolve(strict=False)


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    copilot_home = _copilot_home(context=context)
    configurations = (
        DoctorPathCandidate(
            "mcp-config.json", "global", copilot_home / "mcp-config.json", "Copilot CLI user MCP configuration", True, is_mcp=True
        ),
        DoctorPathCandidate(
            ".mcp.json", "local", context.project_root / ".mcp.json", "Copilot project MCP configuration", True, is_mcp=True
        ),
    )
    instructions = (
        DoctorPathCandidate(
            "copilot-instructions.md",
            "local",
            context.project_root / ".github/copilot-instructions.md",
            "repository-wide Copilot instructions",
            True,
            is_mcp=False,
        ),
        DoctorPathCandidate("AGENTS.md", "local", context.project_root / "AGENTS.md", "shared agent guidance", False, is_mcp=False),
    )
    instruction_roots = (
        DoctorFileRoot("local", context.project_root / ".github/instructions", ("**/*.instructions.md",), "path-scoped Copilot instructions"),
    )
    skill_roots = (
        *shared_skill_roots(context=context),
        ("global", copilot_home / "skills", "Copilot user skill"),
        ("local", context.project_root / ".github/skills", "Copilot project skill"),
    )
    plugin_roots = (
        ("global", copilot_home / "plugins", "Copilot user plugin"),
        ("local", context.project_root / ".github/plugins", "Copilot project plugin"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=instructions,
        instruction_roots=instruction_roots,
        skill_roots=skill_roots,
        plugin_roots=plugin_roots,
        plugin_patterns=("**/plugin.json", "**/package.json"),
    )


DEFINITION = DoctorAgentDefinition(
    agent="copilot",
    display_name="GitHub Copilot CLI",
    executable="copilot",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("COPILOT_HOME is honored when resolving inherited resources.",),
)
