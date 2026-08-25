from collections.abc import Iterable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config import ConfigEntry, ResourceRoot, custom_skill_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import present_resources, resource_candidate, scan_skill_roots


def skills(
    *, context: DoctorContext, config_entries: Iterable[ConfigEntry], configured_extensions: Iterable[DoctorResource]
) -> tuple[DoctorResource, ...]:
    roots: list[ResourceRoot] = [
        ("global", context.omp_home / "skills", "OMP native user skills"),
        ("global", context.omp_home / "managed-skills", "OMP managed user skills"),
        ("global", context.home_directory / ".agent" / "skills", "Agent Skills compatible user source"),
        ("global", context.home_directory / ".agents" / "skills", "Agent Skills compatible user source"),
        ("global", context.codex_home / "skills", "Codex-compatible user skills"),
        ("global", context.claude_home / "skills", "Claude-compatible user skills"),
        ("global", context.xdg_config_directory / "opencode" / "skills", "OpenCode-compatible user skills"),
    ]
    for directory in context.ancestor_directories:
        roots.extend(
            [
                ("local", directory / ".omp" / "skills", "OMP native project skills"),
                ("local", directory / ".agent" / "skills", "Agent Skills compatible project source"),
                ("local", directory / ".agents" / "skills", "Agent Skills compatible project source"),
                ("local", directory / ".claude" / "skills", "Claude-compatible project skills"),
            ]
        )
    roots.extend(
        [
            ("local", context.working_directory / ".codex" / "skills", "Codex-compatible project skills"),
            ("local", context.working_directory / ".opencode" / "skills", "OpenCode-compatible project skills"),
            ("local", context.working_directory / ".github" / "skills", "Copilot-compatible project skills"),
        ]
    )
    roots.extend(custom_skill_roots(config_entries=config_entries))
    roots.extend(
        (resource.origin, resource.path / "skills", "skills supplied by configured OMP extension")
        for resource in configured_extensions
        if resource.state == "configured" and resource.path.is_dir()
    )
    return scan_skill_roots(roots=roots, recursive=True, state="available")


def instructions(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    fixed_sources: list[tuple[DoctorOrigin, Path, str]] = [
        ("global", context.omp_home / "AGENTS.md", "OMP active-profile context"),
        ("global", context.omp_home / "SYSTEM.md", "OMP active-profile system prompt"),
        ("global", context.omp_home / "APPEND_SYSTEM.md", "OMP active-profile system prompt append"),
        ("global", context.omp_home / "RULES.md", "OMP active-profile sticky rules"),
    ]
    for directory in context.ancestor_directories:
        fixed_sources.append(("local", directory / "AGENTS.md", "standalone ancestor context"))
        config_root = directory / ".omp"
        fixed_sources.extend(
            [
                ("local", config_root / "AGENTS.md", "OMP project context"),
                ("local", config_root / "SYSTEM.md", "OMP project system prompt"),
                ("local", config_root / "APPEND_SYSTEM.md", "OMP project system prompt append"),
                ("local", config_root / "RULES.md", "OMP project sticky rules"),
            ]
        )
    resources.extend(
        present_resources(
            candidates=(
                resource_candidate(
                    kind="instructions",
                    is_mcp=False,
                    name=path.name,
                    origin=origin,
                    path=path,
                    present_state="active",
                    detail=detail,
                    include_missing=False,
                )
                for origin, path, detail in fixed_sources
            )
        )
    )
    instruction_roots: list[tuple[DoctorOrigin, Path, str, tuple[str, ...]]] = [
        ("global", context.omp_home / "instructions", "OMP active-profile instructions", ("*.md",)),
        ("global", context.omp_home / "rules", "OMP active-profile rules", ("*.md", "*.mdc")),
    ]
    for directory in context.ancestor_directories:
        instruction_roots.extend(
            [
                ("local", directory / ".omp" / "instructions", "OMP project instructions", ("*.md",)),
                ("local", directory / ".omp" / "rules", "OMP project rules", ("*.md", "*.mdc")),
            ]
        )
    seen_paths = {resource.path for resource in resources}
    for origin, root, detail, patterns in instruction_roots:
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                resolved_path = path.resolve(strict=False)
                if not path.is_file() or resolved_path in seen_paths:
                    continue
                seen_paths.add(resolved_path)
                resources.append(
                    DoctorResource(
                        kind="instructions",
                        is_mcp=False,
                        name=path.name,
                        origin=origin,
                        state="active",
                        path=resolved_path,
                        detail=detail,
                    )
                )
    return tuple(resources)
