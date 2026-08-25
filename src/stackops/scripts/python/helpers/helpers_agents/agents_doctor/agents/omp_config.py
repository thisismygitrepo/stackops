from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping, present_resources, resource_candidate


type ConfigEntry = tuple[DoctorOrigin, Path, Literal["json", "yaml"]]
type ResourceRoot = tuple[DoctorOrigin, Path, str]


def config_entries(*, context: DoctorContext) -> tuple[ConfigEntry, ...]:
    entries: list[ConfigEntry] = [
        ("global", context.omp_home / "config.yml", "yaml"),
        ("global", context.omp_home / "config.yaml", "yaml"),
        ("global", context.omp_home / "settings.json", "json"),
    ]
    for directory in context.ancestor_directories:
        config_root = directory / ".omp"
        entries.extend(
            [
                ("local", config_root / "config.yml", "yaml"),
                ("local", config_root / "config.yaml", "yaml"),
                ("local", config_root / "settings.json", "json"),
                ("local", config_root / "plugin-overrides.json", "json"),
            ]
        )
    return tuple(entries)


def configuration_resources(*, config_entries: Iterable[ConfigEntry]) -> tuple[DoctorResource, ...]:
    return present_resources(
        candidates=(
            resource_candidate(
                kind="configuration",
                is_mcp=False,
                name=path.name,
                origin=origin,
                path=path,
                present_state="active",
                detail="OMP configuration layer",
                include_missing=True,
            )
            for origin, path, _config_format in config_entries
        )
    )


def string_values(*, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(entry for entry in value if isinstance(entry, str) and entry.strip() != "")


def custom_skill_roots(*, config_entries: Iterable[ConfigEntry]) -> tuple[ResourceRoot, ...]:
    roots: list[ResourceRoot] = []
    for origin, config_path, config_format in config_entries:
        if not config_path.is_file():
            continue
        mapping = load_config_mapping(path=config_path, config_format=config_format)
        if isinstance(mapping, str):
            continue
        skills = mapping.get("skills")
        configured_values = string_values(value=mapping.get("skills.customDirectories"))
        if isinstance(skills, dict):
            configured_values = (*configured_values, *string_values(value=skills.get("customDirectories")))
        for value in configured_values:
            root = Path(value).expanduser()
            if not root.is_absolute():
                root = config_path.parent / root
            roots.append((origin, root.resolve(strict=False), f"custom skills configured by {config_path}"))
    return tuple(roots)
