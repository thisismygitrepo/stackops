from dataclasses import replace
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugin_state import plugin_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extension_sources import collect_auto_extensions, read_extension_config
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files, permitted_hook_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResourceState


def collect_omp_hooks(*, context: DoctorContext) -> HookInventory:
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    for origin, root, _detail in plugin_roots(context=context):
        lock_path = root / "omp-plugins.lock.json"
        package_path = root / "package.json"
        mappings = {path: read_extension_config(path=path, context=context, config_format="json") for path in (lock_path, package_path)}
        declarations: dict[str, tuple[object, HookRemoval]] = {}
        for path, mapping in mappings.items():
            if mapping is None:
                continue
            if isinstance(mapping, str):
                diagnostics.append(HookDiagnostic("omp", origin, path, mapping, "error"))
                continue
            key = "plugins" if path == lock_path else "dependencies"
            plugins = mapping.get(key)
            if not isinstance(plugins, dict):
                continue
            for name, value in cast(dict[str, object], plugins).items():
                if name in declarations:
                    continue
                selector = ("plugins", name, "enabled") if path == lock_path else ("dependencies", name)
                removal = HookRemoval(path, "json", selector, "disable" if path == lock_path else "delete")
                declarations[name] = (value, removal)
        for name, (value, removal) in declarations.items():
            state: DoctorResourceState = "disabled" if isinstance(value, dict) and value.get("enabled") is False else "configured"
            entries.append(HookEntry("omp", origin, removal.path, name, "plugin lifecycle (dynamic)", name, state, removal))
    hook_roots: tuple[tuple[DoctorOrigin, Path], ...] = (
        ("global", context.omp_home / "hooks"),
        ("local", context.working_directory / ".omp" / "hooks"),
    )
    for hook_origin, root in hook_roots:
        children = hook_directory_files(directory=root, context=context)
        if isinstance(children, str):
            diagnostics.append(HookDiagnostic("omp", hook_origin, root, children, "error"))
            continue
        for event_directory in children:
            if not permitted_hook_path(path=event_directory, context=context):
                diagnostics.append(HookDiagnostic("omp", hook_origin, event_directory, "Protected hook directory excluded.", "error"))
                continue
            if not event_directory.is_dir():
                continue
            inventory = collect_auto_extensions(agent="omp", origin=hook_origin, directory=event_directory, context=context)
            entries.extend(replace(entry, event=f"""{event_directory.name} (dynamic factory)""") for entry in inventory.entries)
            diagnostics.extend(inventory.diagnostics)
    return HookInventory(tuple(entries), tuple(diagnostics))
