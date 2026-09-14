from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupPlan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources import collect_cleanup_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_workspace import collect_workspace_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.discovery import collect_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext


def inspect_cleanup_agent(*, agent: DoctorAgent, context: DoctorContext) -> HookInventory:
    inventories = (
        collect_hooks(agent=agent, context=context),
        collect_cleanup_resources(agent=agent, context=context, resource_focuses=("mcp", "plugin", "skill", "instructions")),
        collect_cleanup_resources(agent=agent, context=context, resource_focuses=("configuration",)),
    )
    return HookInventory(
        entries=tuple(dict.fromkeys(entry for inventory in inventories for entry in inventory.entries)),
        diagnostics=tuple(dict.fromkeys(diagnostic for inventory in inventories for diagnostic in inventory.diagnostics)),
    )


def cleanup_kind(entry: HookEntry) -> str:
    if entry.event in ("configuration", "mcp", "plugin", "skill", "instructions", "workspace"):
        return entry.event
    return "hook"


def cleanup_action(entry: HookEntry) -> str:
    if entry.removal is None or entry.origin in ("admin", "system"):
        return "Read only"
    match entry.removal.format:
        case "file":
            return "Quarantine whole file"
        case "directory":
            return "Quarantine whole directory"
        case _:
            return "Disable in configuration" if entry.removal.action == "disable" else "Remove from configuration"


def cleanup_details(*, entry: HookEntry, entries: tuple[HookEntry, ...]) -> str:
    details = [
        entry.name, "", f"""Agent: {entry.agent}    Scope: {entry.origin}    State: {entry.state}""",
        f"""Type: {cleanup_kind(entry)}    Event: {entry.event}""", "", "Source", str(entry.path),
        "", "Command / provenance", entry.command or "—", "", "Reset action", cleanup_action(entry),
    ]
    removal = entry.removal
    if removal is not None:
        details.extend((str(removal.path), " / ".join(str(part) for part in removal.selector)))
        linked = tuple(item for item in entries if item != entry and item.removal == removal)
        if linked:
            details.extend(("", "Shares this reset action with", *(f"""• {item.agent}: {item.name}""" for item in linked)))
        if removal.format in ("file", "directory"):
            details.extend(("", "This moves the entire target into backup, including any unselected contents."))
        else:
            details.extend(("", "Review the exact configuration diff before applying this action."))
    return "\n".join(details)


def selected_cleanup_inventory(*, inventory: HookInventory, selected: set[HookRemoval]) -> HookInventory:
    entries = tuple(entry for entry in inventory.entries if entry.removal in selected and entry.origin in ("local", "global"))
    origins = {(entry.agent, entry.origin) for entry in entries}
    return HookInventory(
        entries=entries,
        diagnostics=tuple(diagnostic for diagnostic in inventory.diagnostics if (diagnostic.agent, diagnostic.origin) in origins),
    )


def build_selected_cleanup_plan(*, inventory: HookInventory, context: DoctorContext, recursive: bool) -> CleanupPlan:
    selected_agents: dict[DoctorAgent, None] = {entry.agent: None for entry in inventory.entries if entry.agent != "shared"}
    refreshed = [inspect_cleanup_agent(agent=agent, context=context) for agent in selected_agents]
    if any(entry.agent == "shared" for entry in inventory.entries):
        refreshed.append(collect_workspace_resources(context=context, recursive=recursive))
    entries = {entry for item in refreshed for entry in item.entries}
    if any(entry not in entries for entry in inventory.entries):
        raise ValueError("Selected resources changed since inspection. Refresh and select them again.")
    origins = {(entry.agent, entry.origin) for entry in inventory.entries}
    selected = HookInventory(
        entries=inventory.entries,
        diagnostics=tuple(dict.fromkeys(
            diagnostic for item in refreshed for diagnostic in item.diagnostics if (diagnostic.agent, diagnostic.origin) in origins
        )),
    )
    return build_cleanup_plan(inventory=selected, scope="all", match=None, home_directory=context.home_directory)
