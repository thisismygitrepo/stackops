from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceState
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping, resource_candidate, scan_plugin_roots


def _configuration(
    *, name: str, origin: DoctorOrigin, path: Path, present_state: DoctorResourceState, detail: str
) -> tuple[DoctorResource, dict[str, object]]:
    candidate = resource_candidate(
        kind="configuration", name=name, origin=origin, path=path, present_state=present_state, detail=detail, include_missing=True
    )
    if candidate is None:
        raise RuntimeError(f"Missing Pi configuration candidate for {path}")
    if candidate.state == "missing":
        return candidate, {}

    loaded = load_config_mapping(path=path, config_format="json")
    if isinstance(loaded, str):
        invalid = DoctorResource(
            kind="configuration",
            name=name,
            origin=origin,
            state="configured",
            path=path.resolve(strict=False),
            detail=f"{detail}; invalid JSON: {loaded}",
        )
        return invalid, {}
    return candidate, loaded


def _string_entries(*, settings: dict[str, object], key: str) -> tuple[str, ...]:
    value = settings.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(entry for entry in value if isinstance(entry, str))


def _package_sources(*, settings: dict[str, object]) -> tuple[tuple[str, bool], ...]:
    packages = settings.get("packages")
    if not isinstance(packages, list):
        return ()

    sources: list[tuple[str, bool]] = []
    for package in packages:
        if isinstance(package, str):
            sources.append((package, False))
            continue
        if not isinstance(package, dict):
            continue
        source = package.get("source")
        if isinstance(source, str):
            sources.append((source, True))
    return tuple(sources)


def _setting_path(*, value: str, base_directory: Path) -> Path:
    unprefixed = value[1:] if value.startswith(("!", "+", "-")) else value
    candidate = Path(unprefixed).expanduser()
    return (candidate if candidate.is_absolute() else base_directory / candidate).resolve(strict=False)


def _package_path(*, source: str, base_directory: Path, declaration_path: Path) -> Path:
    candidate = Path(source).expanduser()
    if candidate.is_absolute() or source.startswith((".", "~")):
        return _setting_path(value=source, base_directory=base_directory)
    return declaration_path.resolve(strict=False)


def _settings_plugins(
    *, origin: DoctorOrigin, settings_path: Path, settings: dict[str, object], shadowed_packages: frozenset[str]
) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    base_directory = settings_path.parent

    for source, filtered in _package_sources(settings=settings):
        state: DoctorResourceState = "shadowed" if source in shadowed_packages else "configured"
        filter_detail = " with resource filters" if filtered else ""
        resources.append(
            DoctorResource(
                kind="plugin",
                name=source,
                origin=origin,
                state=state,
                path=_package_path(source=source, base_directory=base_directory, declaration_path=settings_path),
                detail=f"Pi package declared in {settings_path.name}{filter_detail}",
            )
        )

    for entry in _string_entries(settings=settings, key="extensions"):
        disabled = entry.startswith(("!", "-"))
        target = _setting_path(value=entry, base_directory=base_directory)
        state = "disabled" if disabled else ("active" if target.exists() else "configured")
        resources.append(
            DoctorResource(
                kind="plugin",
                name=entry.lstrip("!+-"),
                origin=origin,
                state=state,
                path=target,
                detail=f"Extension path or selection pattern declared in {settings_path.name}",
            )
        )
    return tuple(resources)


def collect_pi_settings_resources(context: DoctorContext) -> tuple[DoctorResource, ...]:
    global_settings_path = context.pi_home / "settings.json"
    local_settings_path = context.working_directory / ".pi" / "settings.json"
    global_settings_resource, global_settings = _configuration(
        name="settings.json", origin="global", path=global_settings_path, present_state="active", detail="Global Pi settings"
    )
    local_settings_resource, local_settings = _configuration(
        name="settings.json",
        origin="local",
        path=local_settings_path,
        present_state="active",
        detail="Project Pi settings; merged over global settings",
    )
    global_mcp, _global_mcp_mapping = _configuration(
        name="mcp.json",
        origin="global",
        path=context.pi_home / "mcp.json",
        present_state="configured",
        detail="Extension-owned MCP configuration; Pi core has no built-in MCP loader",
    )
    local_mcp, _local_mcp_mapping = _configuration(
        name="mcp.json",
        origin="local",
        path=context.working_directory / ".pi" / "mcp.json",
        present_state="configured",
        detail="Extension-owned MCP configuration; Pi core has no built-in MCP loader",
    )

    local_package_sources = frozenset(source for source, _filtered in _package_sources(settings=local_settings))
    plugins = (
        *scan_plugin_roots(
            roots=(
                ("local", context.working_directory / ".pi" / "extensions", "Auto-discovered project extension"),
                ("global", context.pi_home / "extensions", "Auto-discovered global extension"),
            ),
            patterns=("*.ts", "*.js", "*/index.ts", "*/index.js"),
            state="active",
        ),
        *_settings_plugins(origin="local", settings_path=local_settings_path, settings=local_settings, shadowed_packages=frozenset()),
        *_settings_plugins(origin="global", settings_path=global_settings_path, settings=global_settings, shadowed_packages=local_package_sources),
    )
    return global_settings_resource, local_settings_resource, global_mcp, local_mcp, *plugins
