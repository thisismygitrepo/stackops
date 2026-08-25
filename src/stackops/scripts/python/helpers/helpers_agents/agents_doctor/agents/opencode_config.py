from collections.abc import Iterable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping


type OpenCodeConfigPath = tuple[DoctorOrigin, Path]


def config_paths(*, context: DoctorContext) -> tuple[OpenCodeConfigPath, ...]:
    global_root = context.xdg_config_directory / "opencode"
    paths: list[OpenCodeConfigPath] = [("global", global_root / "opencode.json"), ("global", global_root / "opencode.jsonc")]
    for directory in context.ancestor_directories:
        paths.extend(
            [
                ("local", directory / "opencode.json"),
                ("local", directory / "opencode.jsonc"),
                ("local", directory / ".opencode" / "opencode.json"),
                ("local", directory / ".opencode" / "opencode.jsonc"),
            ]
        )
    return tuple(paths)


def configured_values(*, value: object) -> tuple[object, ...]:
    if isinstance(value, list):
        return tuple(value)
    return ()


def configured_plugins(*, config_paths: Iterable[OpenCodeConfigPath]) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    for origin, config_path in config_paths:
        if not config_path.is_file():
            continue
        mapping = load_config_mapping(path=config_path, config_format="json")
        if isinstance(mapping, str):
            continue
        raw_plugins = mapping.get("plugins", mapping.get("plugin"))
        for value in configured_values(value=raw_plugins):
            if isinstance(value, str):
                disabled = value.startswith("-")
                resources.append(
                    DoctorResource(
                        kind="plugin",
                        name=value.removeprefix("-"),
                        origin=origin,
                        state="disabled" if disabled else "configured",
                        path=config_path.resolve(strict=False),
                        detail="OpenCode config entry",
                    )
                )
            elif isinstance(value, dict) and isinstance(value.get("package"), str):
                package = value["package"]
                assert isinstance(package, str)
                resources.append(
                    DoctorResource(
                        kind="plugin",
                        name=package,
                        origin=origin,
                        state="configured",
                        path=config_path.resolve(strict=False),
                        detail="OpenCode config package entry",
                    )
                )
    return tuple(resources)
