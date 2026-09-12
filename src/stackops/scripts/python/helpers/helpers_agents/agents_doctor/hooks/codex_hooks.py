import shlex
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_plugin_hooks import collect_codex_plugin_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extended_constants import CODEX_SYSTEM_ROOT
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extension_sources import read_extension_config
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory import collect_hook_mapping, collect_json_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import (
    HookDiagnostic,
    HookEntry,
    HookInventory,
    HookRemoval,
    HookSource,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResourceState


@dataclass(frozen=True)
class CodexHookLayer:
    origin: DoctorOrigin
    path: Path
    mapping: dict[str, object]
    profile: bool


def _layer_inventory(*, layer: CodexHookLayer, state: DoctorResourceState) -> HookInventory:
    source = HookSource("codex", layer.origin, layer.path, ("hooks",))
    mapping = dict(layer.mapping)
    hooks = mapping.get("hooks")
    if isinstance(hooks, dict):
        mapping["hooks"] = {
            name: value for name, value in cast(dict[str, object], hooks).items() if name not in ("managed_dir", "windows_managed_dir")
        }
    inventory = collect_hook_mapping(source=source, mapping=mapping, state=state, removal=None)
    entries = [replace(entry, removal=replace(entry.removal, format="toml") if entry.removal is not None else None) for entry in inventory.entries]
    diagnostics = list(inventory.diagnostics)
    if "notify" in mapping:
        notify = mapping["notify"]
        if isinstance(notify, list) and all(isinstance(value, str) for value in notify):
            if notify:
                command = shlex.join(cast(list[str], notify))
                removal = HookRemoval(layer.path, "toml", ("notify",), "delete") if layer.origin in ("global", "local") else None
                entries.append(
                    HookEntry(
                        "codex",
                        layer.origin,
                        layer.path,
                        command,
                        "notify",
                        command,
                        "disabled" if layer.origin == "local" else "configured",
                        removal,
                    )
                )
        else:
            diagnostics.append(HookDiagnostic("codex", layer.origin, layer.path, "notify must be an array of command arguments.", "error"))
    return HookInventory(tuple(entries), tuple(diagnostics))


def collect_codex_hooks(*, context: DoctorContext) -> HookInventory:
    paths: list[tuple[DoctorOrigin, Path, bool]] = [
        ("admin", CODEX_SYSTEM_ROOT / "config.toml", False),
        ("admin", CODEX_SYSTEM_ROOT / "requirements.toml", False),
        ("global", context.codex_home / "config.toml", False),
    ]
    paths.extend(("local", directory / ".codex" / "config.toml", False) for directory in context.ancestor_directories)
    diagnostics: list[HookDiagnostic] = []
    children = hook_directory_files(directory=context.codex_home, context=context)
    if isinstance(children, str):
        diagnostics.append(HookDiagnostic("codex", "global", context.codex_home, children, "error"))
    else:
        paths.extend(("global", path, True) for path in children if path.name.endswith(".config.toml"))
    layers: list[CodexHookLayer] = []
    enabled = True
    required_enabled: bool | None = None
    managed_only = False
    for origin, path, profile in paths:
        mapping = read_extension_config(path=path, context=context, config_format="toml")
        if isinstance(mapping, str):
            diagnostics.append(HookDiagnostic("codex", origin, path, mapping, "error"))
        elif mapping is not None:
            layers.append(CodexHookLayer(origin, path, mapping, profile))
            features = mapping.get("features")
            if not profile and isinstance(features, dict):
                value = features.get("hooks", features.get("codex_hooks"))
                if isinstance(value, bool):
                    enabled = value
                    if origin == "admin" and path.name == "requirements.toml":
                        required_enabled = value
            if origin == "admin" and mapping.get("allow_managed_hooks_only") is True:
                managed_only = True
    if required_enabled is not None:
        enabled = required_enabled
    inventories: list[HookInventory] = []
    for layer in layers:
        state: DoctorResourceState = "configured" if enabled and not (managed_only and layer.origin != "admin") else "disabled"
        inventories.append(_layer_inventory(layer=layer, state=state))
    seen_hook_paths: set[Path] = set()
    for origin, config_path, profile in paths:
        hook_path = config_path.with_name("hooks.json")
        if profile or hook_path in seen_hook_paths:
            continue
        seen_hook_paths.add(hook_path)
        state = "configured" if enabled and not (managed_only and origin != "admin") else "disabled"
        inventories.append(collect_json_hooks(source=HookSource("codex", origin, hook_path, ("hooks",)), context=context, state=state, removal=None))
    settings: dict[str, tuple[DoctorOrigin, Path, bool | None]] = {}
    for layer in layers:
        if layer.profile:
            continue
        plugins = layer.mapping.get("plugins")
        if not isinstance(plugins, dict):
            continue
        for name, value in cast(dict[str, object], plugins).items():
            raw_enabled = value.get("enabled") if isinstance(value, dict) else None
            settings[name] = (layer.origin, layer.path, raw_enabled if isinstance(raw_enabled, bool) else None)
    inventories.append(collect_codex_plugin_hooks(context=context, settings=settings, enabled=enabled and not managed_only))
    diagnostics.append(
        HookDiagnostic(
            "codex",
            "global",
            context.codex_home,
            "Configured hooks still require runtime trust; project trust, selected profiles, CLI/SDK injections and cloud/MDM policies are not resolved. Local notify entries are ignored by Codex.",
            "notice",
        )
    )
    return HookInventory(
        tuple(entry for inventory in inventories for entry in inventory.entries),
        (*diagnostics, *(diagnostic for inventory in inventories for diagnostic in inventory.diagnostics)),
    )
