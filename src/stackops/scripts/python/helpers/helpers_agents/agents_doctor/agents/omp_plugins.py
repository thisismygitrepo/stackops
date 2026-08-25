import re
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config import ConfigEntry, ResourceRoot, string_values
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugin_state import plugin_roots, plugin_state_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import (
    load_config_mapping,
    present_resources,
    resource_candidate,
    scan_plugin_roots,
)


_EXTENSION_MODULE_SUFFIXES = frozenset({".cjs", ".js", ".mjs", ".ts"})
_PACKAGE_IDENTIFIER = re.compile(r"(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*", flags=re.IGNORECASE)


def _extension_roots(*, context: DoctorContext) -> tuple[ResourceRoot, ...]:
    roots: list[ResourceRoot] = [("global", context.omp_home / "extensions", "OMP active-profile extensions")]
    roots.extend(("local", directory / ".omp" / "extensions", "OMP project extensions") for directory in context.ancestor_directories)
    return tuple(roots)


def _configured_extension_path(*, value: str, config_path: Path) -> Path | None:
    candidate = Path(value).expanduser()
    if candidate.suffix not in _EXTENSION_MODULE_SUFFIXES and _PACKAGE_IDENTIFIER.fullmatch(value) is not None:
        return None
    path_syntax = (
        candidate.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or value.startswith((".", "~"))
        or "\\" in value
        or ("/" in value and not value.startswith("@"))
        or candidate.suffix in _EXTENSION_MODULE_SUFFIXES
    )
    if not path_syntax:
        return None
    resolved_candidate = candidate if candidate.is_absolute() else config_path.parent / candidate
    return resolved_candidate.resolve(strict=False)


def configured_extensions(*, config_entries: Iterable[ConfigEntry]) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    for origin, config_path, config_format in config_entries:
        if not config_path.is_file():
            continue
        mapping = load_config_mapping(path=config_path, config_format=config_format)
        if isinstance(mapping, str):
            continue
        for value in string_values(value=mapping.get("extensions")):
            extension_path = _configured_extension_path(value=value, config_path=config_path)
            is_package = extension_path is None
            resource_path = config_path.resolve(strict=False) if extension_path is None else extension_path
            resources.append(
                DoctorResource(
                    kind="plugin",
                    name=value,
                    origin=origin,
                    state="configured",
                    path=resource_path,
                    detail=f"OMP extension {'package' if is_package else 'path'} declared in {config_path}",
                )
            )
        for value in string_values(value=mapping.get("disabledExtensions")):
            resources.append(
                DoctorResource(
                    kind="plugin",
                    name=value,
                    origin=origin,
                    state="disabled",
                    path=config_path.resolve(strict=False),
                    detail="disabled by OMP configuration",
                )
            )
    return tuple(resources)


def plugins(*, context: DoctorContext, configured_extensions: Iterable[DoctorResource]) -> tuple[DoctorResource, ...]:
    registry_roots = plugin_roots(context=context)
    extension_roots = _extension_roots(context=context)
    directories = present_resources(
        candidates=(
            resource_candidate(
                kind="plugin", name=path.name, origin=origin, path=path, present_state="active", detail=detail, include_missing=origin == "global"
            )
            for origin, path, detail in (*registry_roots, *extension_roots)
        )
    )
    extension_modules = scan_plugin_roots(roots=extension_roots, patterns=("*.ts", "*.js", "*/index.ts", "*/index.js"), state="active")
    return (*directories, *plugin_state_resources(context=context), *extension_modules, *configured_extensions)
