import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config import ResourceRoot, string_values
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceState
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping, present_resources, resource_candidate


@dataclass(frozen=True)
class _PluginDeclaration:
    name: str
    origin: DoctorOrigin
    registry_root: Path
    declaration_path: Path
    enabled: bool | None


def plugin_roots(*, context: DoctorContext) -> tuple[ResourceRoot, ...]:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    global_root = context.omp_home.parent / "plugins"
    if xdg_data_home is not None and xdg_data_home.strip() != "":
        omp_data_root = context.xdg_data_directory / "omp"
        profile = os.environ.get("OMP_PROFILE")
        if profile is not None and profile.strip() not in ("", "default"):
            omp_data_root = omp_data_root / "profiles" / profile.strip()
        global_root = omp_data_root / "plugins"
    roots: list[ResourceRoot] = [("global", global_root, "OMP active-profile plugin registry")]
    roots.extend(("local", directory / ".omp" / "plugins", "OMP project plugin registry") for directory in context.ancestor_directories)
    return tuple(roots)


def _mapping(*, path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    loaded = load_config_mapping(path=path, config_format="json")
    return {} if isinstance(loaded, str) else loaded


def _root_declarations(*, origin: DoctorOrigin, root: Path) -> tuple[_PluginDeclaration, ...]:
    declarations: dict[str, _PluginDeclaration] = {}
    package_path = root / "package.json"
    dependencies = _mapping(path=package_path).get("dependencies")
    if isinstance(dependencies, dict):
        for name in cast(dict[str, object], dependencies):
            declarations[name] = _PluginDeclaration(name=name, origin=origin, registry_root=root, declaration_path=package_path, enabled=None)

    lock_path = root / "omp-plugins.lock.json"
    lock_plugins = _mapping(path=lock_path).get("plugins")
    if isinstance(lock_plugins, dict):
        for name, raw_settings in cast(dict[str, object], lock_plugins).items():
            raw_enabled = raw_settings.get("enabled") if isinstance(raw_settings, dict) else None
            enabled = raw_enabled if isinstance(raw_enabled, bool) else None
            declarations[name] = _PluginDeclaration(name=name, origin=origin, registry_root=root, declaration_path=lock_path, enabled=enabled)
    return tuple(declarations.values())


def _disabled_names(*, context: DoctorContext) -> frozenset[str]:
    disabled: set[str] = set()
    for directory in context.ancestor_directories:
        mapping = _mapping(path=directory / ".omp" / "plugin-overrides.json")
        disabled.update(string_values(value=mapping.get("disabled")))
    return frozenset(disabled)


def _state_files(*, roots: Iterable[ResourceRoot]) -> tuple[DoctorResource, ...]:
    candidates: list[DoctorResource | None] = []
    for origin, root, _detail in roots:
        for name in ("package.json", "omp-plugins.lock.json"):
            candidates.append(
                resource_candidate(
                    kind="configuration",
                    is_mcp=False,
                    name=name,
                    origin=origin,
                    path=root / name,
                    present_state="active",
                    detail="OMP plugin registry state",
                    include_missing=origin == "global" or root.is_dir(),
                )
            )
    return present_resources(candidates=candidates)


def _plugin_skills(*, declaration: _PluginDeclaration, package_root: Path) -> tuple[DoctorResource, ...]:
    skills_root = package_root / "skills"
    if not skills_root.is_dir():
        return ()
    return tuple(
        DoctorResource(
            kind="skill",
            is_mcp=False,
            name=path.parent.name,
            origin=declaration.origin,
            state="available",
            path=path.resolve(strict=False),
            detail=f"skill supplied by active OMP plugin {declaration.name}",
        )
        for path in sorted(skills_root.rglob("SKILL.md"))
        if path.is_file()
    )


def plugin_state_resources(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    roots = plugin_roots(context=context)
    declarations = tuple(declaration for origin, root, _detail in roots for declaration in _root_declarations(origin=origin, root=root))
    winning_positions: dict[str, int] = {}
    for position, declaration in enumerate(declarations):
        winning_positions[declaration.name] = position

    disabled_names = _disabled_names(context=context)
    resources: list[DoctorResource] = list(_state_files(roots=roots))
    for position, declaration in enumerate(declarations):
        package_root = declaration.registry_root / "node_modules" / declaration.name
        manifest_path = package_root / "package.json"
        manifest = _mapping(path=manifest_path)
        installed = manifest_path.is_file()
        plugin_manifest = "omp" in manifest or "pi" in manifest
        raw_version = manifest.get("version")
        version_detail = f"; version {raw_version}" if isinstance(raw_version, str) else ""
        if winning_positions[declaration.name] != position:
            state: DoctorResourceState = "shadowed"
            status_detail = "shadowed by a project plugin registry"
        elif declaration.name in disabled_names or declaration.enabled is False:
            state = "disabled"
            status_detail = "disabled by plugin state or project overrides"
        elif installed and plugin_manifest:
            state = "active"
            status_detail = "installed and enabled"
        elif installed:
            state = "configured"
            status_detail = "installed, but package.json has no omp or pi plugin manifest"
        else:
            state = "configured"
            status_detail = "declared but not present under node_modules"
        resources.append(
            DoctorResource(
                kind="plugin",
                is_mcp=False,
                name=declaration.name,
                origin=declaration.origin,
                state=state,
                path=package_root.resolve(strict=False) if installed else declaration.declaration_path.resolve(strict=False),
                detail=f"{status_detail}{version_detail}; declared in {declaration.declaration_path}",
            )
        )
        if state == "active":
            resources.extend(_plugin_skills(declaration=declaration, package_root=package_root))
    return tuple(resources)
