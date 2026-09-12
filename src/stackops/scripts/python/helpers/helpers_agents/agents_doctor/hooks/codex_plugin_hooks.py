from dataclasses import replace
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory import collect_hook_mapping, collect_json_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import (
    HookDiagnostic,
    HookInventory,
    HookRemoval,
    HookSelector,
    HookSource,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files, permitted_hook_path, read_hook_mapping
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResourceState


def _manifest_hooks(
    *, context: DoctorContext, path: Path, plugin_id: str, origin: DoctorOrigin, state: DoctorResourceState, removal: HookRemoval | None
) -> HookInventory:
    mapping = read_hook_mapping(path=path, context=context)
    if mapping is None:
        return HookInventory((), ())
    if isinstance(mapping, str):
        return HookInventory((), (HookDiagnostic("codex", origin, path, mapping, "error"),))
    root = path.parent.parent
    raw_hooks = mapping.get("hooks", "./hooks/hooks.json")
    declarations: tuple[tuple[object, HookSelector], ...]
    if isinstance(raw_hooks, list):
        declarations = tuple((value, ("hooks", index)) for index, value in enumerate(cast(list[object], raw_hooks)))
    else:
        declarations = ((raw_hooks, ("hooks",)),)
    inventories: list[HookInventory] = []
    diagnostics: list[HookDiagnostic] = []
    for value, selector in declarations:
        if isinstance(value, str):
            target = root / value
            if not value.startswith("./") or ".." in Path(value).parts or not permitted_hook_path(path=target, context=context):
                diagnostics.append(HookDiagnostic("codex", origin, path, f"""Plugin {plugin_id} has an excluded hook path: {value}.""", "error"))
                continue
            if not target.resolve(strict=False).is_relative_to(root.resolve(strict=False)):
                diagnostics.append(HookDiagnostic("codex", origin, path, f"""Plugin {plugin_id} hook path escapes its installation.""", "error"))
                continue
            if "hooks" in mapping and not target.is_file():
                diagnostics.append(HookDiagnostic("codex", origin, target, f"""Plugin {plugin_id} declares a missing hook file.""", "error"))
                continue
            inventory = collect_json_hooks(source=HookSource("codex", origin, target, ("hooks",)), context=context, state=state, removal=removal)
        elif isinstance(value, dict):
            inventory = collect_hook_mapping(
                source=HookSource("codex", origin, path, (*selector, "hooks")), mapping=mapping, state=state, removal=removal
            )
        else:
            diagnostics.append(HookDiagnostic("codex", origin, path, f"""Plugin {plugin_id} has an invalid hooks manifest entry.""", "error"))
            continue
        entries = tuple(replace(entry, name=f"""{plugin_id}: {entry.name}""", removal=removal) for entry in inventory.entries)
        inventories.append(HookInventory(entries, inventory.diagnostics))
    return HookInventory(
        tuple(entry for inventory in inventories for entry in inventory.entries),
        (*diagnostics, *(diagnostic for inventory in inventories for diagnostic in inventory.diagnostics)),
    )


def collect_codex_plugin_hooks(
    *, context: DoctorContext, settings: dict[str, tuple[DoctorOrigin, Path, bool | None]], enabled: bool
) -> HookInventory:
    roots = [context.codex_home / "plugins" / "cache"]
    diagnostics: list[HookDiagnostic] = []
    for _depth in range(3):
        children: list[Path] = []
        for root in roots:
            contents = hook_directory_files(directory=root, context=context)
            if isinstance(contents, str):
                diagnostics.append(HookDiagnostic("codex", "global", root, contents, "error"))
                continue
            for child in contents:
                if not permitted_hook_path(path=child, context=context):
                    diagnostics.append(HookDiagnostic("codex", "global", child, "Protected plugin path was excluded.", "error"))
                elif child.is_dir():
                    children.append(child)
        roots = children
    inventories: list[HookInventory] = []
    for root in roots:
        plugin_id = f"""{root.parent.name}@{root.parent.parent.name}"""
        setting = settings.get(plugin_id)
        origin: DoctorOrigin = "global" if setting is None else setting[0]
        if setting is None:
            state: DoctorResourceState = "available"
            removal = None
        else:
            state = "disabled" if setting[2] is False or not enabled else "configured"
            removal = HookRemoval(setting[1], "toml", ("plugins", plugin_id, "enabled"), "disable") if origin in ("global", "local") else None
        inventories.append(
            _manifest_hooks(
                context=context, path=root / ".codex-plugin" / "plugin.json", plugin_id=plugin_id, origin=origin, state=state, removal=removal
            )
        )
    return HookInventory(
        tuple(entry for inventory in inventories for entry in inventory.entries),
        (*diagnostics, *(diagnostic for inventory in inventories for diagnostic in inventory.diagnostics)),
    )
