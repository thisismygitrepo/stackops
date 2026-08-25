from dataclasses import dataclass
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.codex_config import CodexConfigLayer
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorResource, DoctorResourceState


@dataclass(frozen=True)
class CodexPluginSetting:
    plugin_id: str
    enabled: bool | None
    layer: CodexConfigLayer


def plugin_settings(*, layers: tuple[CodexConfigLayer, ...]) -> tuple[CodexPluginSetting, ...]:
    settings: list[CodexPluginSetting] = []
    for layer in layers:
        if layer.mapping is None:
            continue
        raw_plugins = layer.mapping.get("plugins")
        if not isinstance(raw_plugins, dict):
            continue
        plugins = cast(dict[str, object], raw_plugins)
        for plugin_id, raw_setting in sorted(plugins.items()):
            if not isinstance(raw_setting, dict):
                continue
            setting = cast(dict[str, object], raw_setting)
            raw_enabled = setting.get("enabled")
            enabled = raw_enabled if isinstance(raw_enabled, bool) else None
            settings.append(CodexPluginSetting(plugin_id=plugin_id, enabled=enabled, layer=layer))
    return tuple(settings)


def _setting_detail(*, setting: CodexPluginSetting) -> str:
    if setting.enabled is True:
        return "enabled"
    if setting.enabled is False:
        return "disabled"
    return "enabled state is not explicit"


def plugin_setting_resources(*, settings: tuple[CodexPluginSetting, ...]) -> tuple[tuple[DoctorResource, ...], dict[str, CodexPluginSetting]]:
    winning_positions: dict[str, int] = {}
    for position, setting in enumerate(settings):
        winning_positions[setting.plugin_id] = position

    resources: list[DoctorResource] = []
    effective: dict[str, CodexPluginSetting] = {}
    for position, setting in enumerate(settings):
        detail = _setting_detail(setting=setting)
        if winning_positions[setting.plugin_id] != position:
            state: DoctorResourceState = "shadowed"
            configured_detail = "configured" if setting.enabled is None else detail
            detail = f"{configured_detail} here, but shadowed by a higher-precedence config layer"
        else:
            effective[setting.plugin_id] = setting
            state = "active" if setting.enabled is True else "disabled" if setting.enabled is False else "configured"
        resources.append(
            DoctorResource(
                kind="plugin",
                name=setting.plugin_id,
                origin=setting.layer.origin,
                state=state,
                path=setting.layer.path,
                detail=f"""[plugins."{setting.plugin_id}"] is {detail}""",
            )
        )
    return tuple(resources), effective
