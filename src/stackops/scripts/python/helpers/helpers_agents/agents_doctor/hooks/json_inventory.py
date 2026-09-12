import json
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import (
    HookDiagnostic,
    HookEntry,
    HookInventory,
    HookRemoval,
    HookSelector,
    HookSource,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import read_hook_mapping
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorResourceState


def _hook_command(*, mapping: dict[str, object]) -> str:
    commands = [f"""{key}: {mapping[key]}""" for key in ("command", "bash", "powershell", "prompt", "url", "tool", "function") if key in mapping]
    return "; ".join(commands) if commands else json.dumps(mapping, ensure_ascii=False, sort_keys=True)


def _event_entries(
    *, source: HookSource, event: str, value: object, selector: HookSelector, state: DoctorResourceState, removal: HookRemoval | None
) -> HookInventory:
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    if not isinstance(value, list):
        return HookInventory(
            (), (HookDiagnostic(source.agent, source.origin, source.path, f"""Hook event {event} must contain an array.""", "error"),)
        )
    for index, item in enumerate(cast(list[object], value)):
        item_selector = (*selector, index)
        if not isinstance(item, dict):
            diagnostics.append(HookDiagnostic(source.agent, source.origin, source.path, f"""Malformed hook at {item_selector}.""", "error"))
            continue
        hook = cast(dict[str, object], item)
        if "hooks" in hook:
            nested = _event_entries(source=source, event=event, value=hook["hooks"], selector=(*item_selector, "hooks"), state=state, removal=removal)
            entries.extend(nested.entries)
            diagnostics.extend(nested.diagnostics)
            continue
        command = _hook_command(mapping=hook)
        name = str(hook.get("name") or command)
        item_state: DoctorResourceState = "disabled" if hook.get("enabled") is False or hook.get("disabled") is True else state
        action = removal or HookRemoval(source.path, "json", item_selector, "delete")
        if source.origin in ("admin", "system"):
            action = None
        entries.append(HookEntry(source.agent, source.origin, source.path, name, event, command, item_state, action))
    return HookInventory(tuple(entries), tuple(diagnostics))


def collect_hook_mapping(*, source: HookSource, mapping: dict[str, object], state: DoctorResourceState, removal: HookRemoval | None) -> HookInventory:
    value: object = mapping
    for component in source.selector:
        if isinstance(component, str) and isinstance(value, dict):
            selected = value
            if component not in selected:
                return HookInventory((), ())
            value = selected[component]
        elif isinstance(component, int) and isinstance(value, list) and component < len(cast(list[object], value)):
            value = cast(list[object], value)[component]
        else:
            return HookInventory(
                (), (HookDiagnostic(source.agent, source.origin, source.path, f"""Invalid hook selector {source.selector}.""", "error"),)
            )
    if not isinstance(value, dict):
        return HookInventory((), (HookDiagnostic(source.agent, source.origin, source.path, "Hooks must be an event-to-array object.", "error"),))
    effective_state: DoctorResourceState = "disabled" if mapping.get("disableAllHooks") is True or mapping.get("hooksDisabled") is True else state
    inventories = tuple(
        _event_entries(source=source, event=event, value=items, selector=(*source.selector, event), state=effective_state, removal=removal)
        for event, items in cast(dict[str, object], value).items()
    )
    return HookInventory(
        tuple(entry for result in inventories for entry in result.entries), tuple(error for result in inventories for error in result.diagnostics)
    )


def collect_json_hooks(*, source: HookSource, context: DoctorContext, state: DoctorResourceState, removal: HookRemoval | None) -> HookInventory:
    mapping = read_hook_mapping(path=source.path, context=context)
    if mapping is None:
        return HookInventory((), ())
    if isinstance(mapping, str):
        return HookInventory((), (HookDiagnostic(source.agent, source.origin, source.path, mapping, "error"),))
    return collect_hook_mapping(source=source, mapping=mapping, state=state, removal=removal)
