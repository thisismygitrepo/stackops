import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import (
    DoctorFileRoot,
    DoctorPathCandidate,
    collect_standard_resources,
    shared_skill_roots,
)


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    global_root = context.home_directory / ".cline"
    local_root = context.project_root / ".cline"
    data_root = Path(os.environ.get("CLINE_DATA_DIR", str(global_root / "data"))).expanduser()
    configurations = (
        DoctorPathCandidate("mcp.json", "global", global_root / "mcp.json", "Cline CLI user MCP configuration", True, is_mcp=True),
        DoctorPathCandidate("mcp.json", "local", local_root / "mcp.json", "Cline CLI project MCP configuration", True, is_mcp=True),
        DoctorPathCandidate("agents.yaml", "local", local_root / "agents.yaml", "Cline CLI custom agent definitions", False, is_mcp=False),
        DoctorPathCandidate(
            "cline_mcp_settings.json",
            "global",
            data_root / "settings/cline_mcp_settings.json",
            "Cline extension user MCP configuration",
            False,
            is_mcp=True,
        ),
        DoctorPathCandidate(
            "cline_mcp_settings.json",
            "local",
            local_root / "data/settings/cline_mcp_settings.json",
            "Cline extension project MCP configuration",
            False,
            is_mcp=True,
        ),
    )
    instruction_roots = (
        DoctorFileRoot("local", context.project_root / ".clinerules", ("*.md", "**/*.md"), "Cline extension project rule"),
        DoctorFileRoot("global", data_root / "settings/rules", ("**/*.md",), "Cline CLI user rule"),
        DoctorFileRoot("local", local_root / "rules", ("**/*.md",), "Cline CLI project rule"),
    )
    skill_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        *shared_skill_roots(context=context),
        ("global", global_root / "skills", "Cline user skill"),
        ("global", data_root / "settings/skills", "Cline CLI user skill"),
        ("local", local_root / "skills", "Cline project skill"),
    )
    plugin_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("global", global_root / "plugins", "Cline CLI user plugin"),
        ("local", local_root / "plugins", "Cline CLI project plugin"),
    )
    return collect_standard_resources(
        configurations=configurations,
        instructions=(),
        instruction_roots=instruction_roots,
        skill_roots=skill_roots,
        plugin_roots=plugin_roots,
        plugin_patterns=("**/package.json", "**/*.ts", "**/*.js"),
    )


DEFINITION = DoctorAgentDefinition(
    agent="cline",
    display_name="Cline",
    executable="cline",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=("Cline CLI and extension MCP, rules, skills, plugins and custom agents are reported. CLINE_DATA_DIR is honored.",),
)
