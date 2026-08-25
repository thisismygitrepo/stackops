import os
from collections.abc import Iterable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode_config import (
    OpenCodeConfigPath,
    config_paths,
    configured_plugins,
    configured_values,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import (
    load_config_mapping,
    present_resources,
    resource_candidate,
    scan_plugin_roots,
    scan_skill_roots,
)


def _skills(*, context: DoctorContext, config_paths: Iterable[OpenCodeConfigPath]) -> tuple[DoctorResource, ...]:
    roots: list[tuple[DoctorOrigin, Path, str]] = [
        ("global", context.xdg_config_directory / "opencode" / "skills", "OpenCode user skills"),
        ("global", context.home_directory / ".agents" / "skills", "shared user skills"),
    ]
    for directory in context.ancestor_directories:
        roots.extend(
            [
                ("local", directory / ".opencode" / "skills", "OpenCode project skills"),
                ("local", directory / ".agents" / "skills", "shared project skills"),
            ]
        )
    configured_sources: list[DoctorResource] = []
    for origin, config_path in config_paths:
        if not config_path.is_file():
            continue
        mapping = load_config_mapping(path=config_path, config_format="json")
        if isinstance(mapping, str):
            continue
        for value in configured_values(value=mapping.get("skills")):
            if not isinstance(value, str):
                continue
            if value.startswith(("http://", "https://")):
                configured_sources.append(
                    DoctorResource(
                        kind="skill",
                        name=value,
                        origin=origin,
                        state="configured",
                        path=config_path.resolve(strict=False),
                        detail="remote skill catalog configured by OpenCode",
                    )
                )
                continue
            configured_root = Path(value).expanduser()
            if not configured_root.is_absolute():
                configured_root = context.working_directory / configured_root
            roots.append((origin, configured_root.resolve(strict=False), "configured OpenCode skill source"))
    claude_roots: list[tuple[DoctorOrigin, Path, str]] = [("global", context.claude_home / "skills", "Claude-compatible user skills")]
    claude_roots.extend(("local", directory / ".claude" / "skills", "Claude-compatible project skills") for directory in context.ancestor_directories)
    claude_skills_disabled = os.environ.get("OPENCODE_DISABLE_CLAUDE_CODE") == "1" or os.environ.get("OPENCODE_DISABLE_CLAUDE_CODE_SKILLS") == "1"
    return (
        *scan_skill_roots(roots=roots, recursive=True, state="available"),
        *scan_skill_roots(roots=claude_roots, recursive=True, state="disabled" if claude_skills_disabled else "available"),
        *configured_sources,
    )


def _ambient_instruction_directories(*, context: DoctorContext) -> tuple[Path, ...]:
    if context.working_directory.is_relative_to(context.home_directory):
        directories: list[Path] = []
        directory = context.working_directory
        while True:
            directories.append(directory)
            if directory == context.home_directory:
                return tuple(directories)
            directory = directory.parent
    return tuple(reversed(context.ancestor_directories))


def _instructions(*, context: DoctorContext, config_paths: Iterable[OpenCodeConfigPath]) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    global_path = context.xdg_config_directory / "opencode" / "AGENTS.md"
    if global_path.is_file():
        resources.append(
            DoctorResource(
                kind="instructions",
                name="AGENTS.md",
                origin="global",
                state="active",
                path=global_path.resolve(strict=False),
                detail="loaded first as inherited OpenCode guidance",
            )
        )
    project_disabled = os.environ.get("OPENCODE_DISABLE_PROJECT_CONFIG") == "1"
    for directory in _ambient_instruction_directories(context=context):
        path = directory / "AGENTS.md"
        if path.is_file():
            resources.append(
                DoctorResource(
                    kind="instructions",
                    name="AGENTS.md",
                    origin="local",
                    state="disabled" if project_disabled else "active",
                    path=path.resolve(strict=False),
                    detail="ambient project guidance" if not project_disabled else "disabled by OPENCODE_DISABLE_PROJECT_CONFIG=1",
                )
            )
    for origin, config_path in config_paths:
        if not config_path.is_file():
            continue
        mapping = load_config_mapping(path=config_path, config_format="json")
        if isinstance(mapping, str):
            continue
        for value in configured_values(value=mapping.get("instructions")):
            if isinstance(value, str):
                resources.append(
                    DoctorResource(
                        kind="instructions",
                        name=value,
                        origin=origin,
                        state="configured",
                        path=config_path.resolve(strict=False),
                        detail="retained in V2 config but not loaded into model context",
                    )
                )
    return tuple(resources)


def collect(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    resolved_config_paths = config_paths(context=context)
    config_resources = present_resources(
        candidates=(
            resource_candidate(
                kind="configuration",
                name=path.name,
                origin=origin,
                path=path,
                present_state="active",
                detail="OpenCode configuration layer",
                include_missing=True,
            )
            for origin, path in resolved_config_paths
        )
    )
    plugin_roots: list[tuple[DoctorOrigin, Path, str]] = [("global", context.xdg_config_directory / "opencode" / "plugins", "OpenCode user plugin")]
    plugin_roots.extend(("local", directory / ".opencode" / "plugins", "OpenCode project plugin") for directory in context.ancestor_directories)
    plugins = scan_plugin_roots(roots=plugin_roots, patterns=("*.ts", "*.js", "*/index.ts", "*/index.js", "*/package.json"), state="active")
    return (
        *config_resources,
        *configured_plugins(config_paths=resolved_config_paths),
        *plugins,
        *_skills(context=context, config_paths=resolved_config_paths),
        *_instructions(context=context, config_paths=resolved_config_paths),
    )


DEFINITION = DoctorAgentDefinition(
    agent="opencode",
    display_name="OpenCode",
    executable="opencode",
    version_arguments=("--version",),
    support_level="focused",
    collector=collect,
    notes=("Configured instruction arrays are reported, but OpenCode V2 currently keeps them out of model context.",),
)
