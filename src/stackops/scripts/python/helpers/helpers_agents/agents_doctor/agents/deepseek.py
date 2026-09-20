import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.deepseek_config import deepseek_home, deepseek_patch_inventory, deepseek_patch_paths
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import scan_skill_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.standard import DoctorPathCandidate, collect_standard_resources


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    home = deepseek_home(context=context)
    patches = deepseek_patch_paths(context=context)
    configurations = (
        DoctorPathCandidate("settings.yaml", "global", home / "settings.yaml", "DeepSeek user settings", True, is_mcp=False),
        *(DoctorPathCandidate(path.name, origin, path, "DeepSeek Cordis plugin patches", True, is_mcp=True) for origin, path in patches),
        *(DoctorPathCandidate(
            "package.json", origin, path.parent / "package.json", "DeepSeek profile bundles and dependencies", False, is_mcp=False,
        ) for origin, path in patches if path.parent.parent == home / "profiles"),
    )
    instructions = (
        DoctorPathCandidate("AGENTS.md", "global", home / "AGENTS.md", "DeepSeek user guidance", False, is_mcp=False),
        *(DoctorPathCandidate(name, "local", directory / name, "DeepSeek project guidance", False, is_mcp=False)
          for directory in context.ancestor_directories for name in ("AGENTS.md", "CLAUDE.md", "AGENTS.local.md", "CLAUDE.local.md")),
    )
    configured_agents_home = os.environ.get("DSH_AGENTS_HOME")
    agents_home = Path(configured_agents_home).expanduser() if configured_agents_home else context.home_directory / ".agents"
    if not agents_home.is_absolute():
        agents_home = context.working_directory / agents_home
    skill_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("local", context.project_root / ".dsh" / "skills", "DeepSeek project skill"),
        ("local", context.project_root / ".agents" / "skills", "Shared project skill"),
        ("global", home / "skills", "DeepSeek user skill"),
        ("global", agents_home / "skills", "Shared user skill"),
    )
    skills = [resource for resource in scan_skill_roots(roots=skill_roots, recursive=False, state="available")
              if resource.path.parent != home / "skills" / ".system"]
    for origin, root, detail in skill_roots:
        if not permitted_resource_path(path=root, home_directory=context.home_directory) or not root.is_dir():
            continue
        skills.extend(DoctorResource("skill", False, path.stem, origin, "available", path, detail)
                      for path in sorted(root.glob("*.md"))
                      if permitted_resource_path(path=path, home_directory=context.home_directory) and path.is_file())
    inventory = deepseek_patch_inventory(context=context, paths=patches, focuses=("all",))
    plugins = tuple(DoctorResource(
        "plugin", entry.event == "mcp", entry.name, entry.origin, entry.state, entry.path,
        f"""Configured Cordis entry: {entry.command}""",
    ) for entry in inventory.entries)
    return (
        *collect_standard_resources(
            configurations=configurations, instructions=instructions, instruction_roots=(), skill_roots=(), plugin_roots=(), plugin_patterns=(),
        ),
        *plugins,
        *skills,
    )


DEFINITION = DoctorAgentDefinition(
    agent="deepseek",
    display_name="DeepSeek Harness",
    executable="dsh",
    version_arguments=("--version",),
    support_level="standard",
    collector=collect,
    notes=(
        "DSH_HOME and DSH_AGENTS_HOME are honored. Profile patches are listed for inspection; only the selected profile loads.",
        "StackOps loads the project .dsh/cordis.patch.yml explicitly. Additional CLI patches and dynamically registered resources require inspection in DeepSeek.",
    ),
)
