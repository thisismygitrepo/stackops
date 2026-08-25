from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_plugins import CodexPluginSetting
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceState
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping, scan_skill_roots


@dataclass(frozen=True)
class _PluginManifest:
    plugin_id: str
    version: str
    path: Path
    skill_root: Path | None
    error: str | None


def _load_plugin_manifest(*, path: Path) -> _PluginManifest:
    source = path.parents[3].name
    cache_name = path.parents[2].name
    cached_version = path.parents[1].name
    plugin_id = f"{cache_name}@{source}"
    loaded = load_config_mapping(path=path, config_format="json")
    if isinstance(loaded, str):
        return _PluginManifest(plugin_id=plugin_id, version=cached_version, path=path, skill_root=None, error=loaded.replace("\n", " "))
    raw_version = loaded.get("version")
    version = raw_version if isinstance(raw_version, str) and raw_version.strip() != "" else cached_version
    raw_skills = loaded.get("skills")
    skill_root = path.parent.parent.joinpath(raw_skills).resolve(strict=False) if isinstance(raw_skills, str) else None
    return _PluginManifest(plugin_id=plugin_id, version=version, path=path, skill_root=skill_root, error=None)


def cached_plugins(
    *, context: DoctorContext, effective_settings: dict[str, CodexPluginSetting]
) -> tuple[tuple[DoctorResource, ...], tuple[DoctorResource, ...]]:
    cache_root = context.codex_home / "plugins" / "cache"
    manifests = tuple(_load_plugin_manifest(path=path) for path in sorted(cache_root.glob("*/*/*/.codex-plugin/plugin.json")))
    resources: list[DoctorResource] = []
    enabled_skill_roots: list[tuple[DoctorOrigin, Path, str]] = []
    for manifest in manifests:
        setting = effective_settings.get(manifest.plugin_id)
        source = manifest.path.parents[3].name
        origin: DoctorOrigin = "system" if source in ("openai-bundled", "openai-primary-runtime") else "global"
        if setting is None:
            state: DoctorResourceState = "available"
        elif setting.enabled is True:
            state = "active"
        elif setting.enabled is False:
            state = "disabled"
        else:
            state = "configured"
        detail = f"cached Codex plugin manifest; version {manifest.version}"
        if manifest.error is not None:
            detail = f"{detail}; JSON could not be parsed: {manifest.error}"
        resources.append(
            DoctorResource(kind="plugin", is_mcp=False, name=manifest.plugin_id, origin=origin, state=state, path=manifest.path, detail=detail)
        )
        if setting is not None and setting.enabled is True and manifest.skill_root is not None:
            enabled_skill_roots.append((origin, manifest.skill_root, f"skill bundled by enabled plugin {manifest.plugin_id}"))
    plugin_skills = scan_skill_roots(roots=enabled_skill_roots, recursive=True, state="available")
    return tuple(resources), plugin_skills
