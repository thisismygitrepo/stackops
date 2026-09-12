from dataclasses import replace
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory import collect_hook_mapping, collect_json_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import (
    HookDiagnostic,
    HookEntry,
    HookInventory,
    HookRemoval,
    HookSource,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import read_hook_mapping
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorResourceState


def _plugin_hooks(*, root: Path, source: HookSource, context: DoctorContext, state: DoctorResourceState, removal: HookRemoval) -> HookInventory:
    manifest = read_hook_mapping(path=root / ".claude-plugin/plugin.json", context=context)
    if isinstance(manifest, str):
        return HookInventory((), (HookDiagnostic(source.agent, source.origin, root, manifest, "error"),))
    declared = manifest.get("hooks") if isinstance(manifest, dict) else None
    components = cast(list[object], declared) if isinstance(declared, list) else [declared] if declared is not None else []
    inventories = [
        collect_json_hooks(source=replace(source, path=root / "hooks/hooks.json", selector=("hooks",)), context=context, state=state, removal=removal)
    ]
    for component in components:
        if isinstance(component, str):
            inventories.append(
                collect_json_hooks(source=replace(source, path=root / component, selector=("hooks",)), context=context, state=state, removal=removal)
            )
        elif isinstance(component, dict):
            inventories.append(
                collect_hook_mapping(
                    source=replace(source, path=root / ".claude-plugin/plugin.json", selector=("hooks",)),
                    mapping=cast(dict[str, object], component),
                    state=state,
                    removal=removal,
                )
            )
        else:
            inventories.append(HookInventory((), (HookDiagnostic(source.agent, source.origin, root, "Invalid plugin hooks declaration.", "error"),)))
    return HookInventory(
        tuple(dict.fromkeys(entry for inventory in inventories for entry in inventory.entries)),
        tuple(error for inventory in inventories for error in inventory.diagnostics),
    )


def collect_claude_plugin_hooks(*, context: DoctorContext, sources: tuple[HookSource, ...]) -> HookInventory:
    index_path = context.claude_home / "plugins/installed_plugins.json"
    index = read_hook_mapping(path=index_path, context=context)
    if isinstance(index, str):
        return HookInventory((), (HookDiagnostic("claude", "global", index_path, index, "error"),))
    installed: dict[str, object] = {}
    if index is not None:
        raw_plugins = index.get("plugins")
        if not isinstance(raw_plugins, dict):
            return HookInventory(
                (), (HookDiagnostic("claude", "global", index_path, "Plugin installation registry must contain a plugins object.", "error"),)
            )
        installed = cast(dict[str, object], raw_plugins)
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    for source in sources:
        settings = read_hook_mapping(path=source.path, context=context)
        if not isinstance(settings, dict):
            continue
        raw_enabled = settings.get("enabledPlugins", {})
        if not isinstance(raw_enabled, dict):
            diagnostics.append(HookDiagnostic("claude", source.origin, source.path, "enabledPlugins must be an object.", "error"))
            continue
        for plugin_name, enabled in cast(dict[str, object], raw_enabled).items():
            records = installed.get(plugin_name, [])
            if not isinstance(records, list):
                diagnostics.append(
                    HookDiagnostic("claude", source.origin, index_path, f"""Invalid installation records for {plugin_name}.""", "error")
                )
                continue
            matched = False
            for raw_record in cast(list[object], records):
                if not isinstance(raw_record, dict):
                    continue
                record = cast(dict[str, object], raw_record)
                install_path = record.get("installPath")
                project_path = record.get("projectPath")
                if isinstance(project_path, str) and Path(project_path) not in context.ancestor_directories:
                    continue
                if not isinstance(install_path, str):
                    continue
                matched = True
                state: DoctorResourceState = "disabled" if enabled is False or settings.get("disableAllHooks") is True else "configured"
                removal = HookRemoval(source.path, "json", ("enabledPlugins", plugin_name), "disable")
                inventory = _plugin_hooks(root=Path(install_path).expanduser(), source=source, context=context, state=state, removal=removal)
                entries.extend(replace(entry, name=f"""{plugin_name}: {entry.name}""") for entry in inventory.entries)
                diagnostics.extend(inventory.diagnostics)
            if not matched and enabled is not False:
                diagnostics.append(
                    HookDiagnostic(
                        "claude",
                        source.origin,
                        source.path,
                        f"""Enabled plugin {plugin_name} has no inspectable installation; its hooks are unknown.""",
                        "error",
                    )
                )
    return HookInventory(tuple(dict.fromkeys(entries)), tuple(dict.fromkeys(diagnostics)))
