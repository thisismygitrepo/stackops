from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_configuration import configuration_cleanup
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resource_roots import reset_plugin_roots, validate_resource_location
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorResourceFocus
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_DEFINITION_BY_AGENT
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.resource_inventory import collect_agent_resources


def collect_cleanup_resources(
    *, agent: DoctorAgent, context: DoctorContext, resource_focuses: tuple[DoctorResourceFocus, ...]
) -> HookInventory:
    resources = collect_agent_resources(definition=DOCTOR_DEFINITION_BY_AGENT[agent], context=context)
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    configurations = {resource.path for resource in resources if resource.kind == "configuration"}
    resetting_all = "all" in resource_focuses
    roots = reset_plugin_roots(agent=agent, context=context) if resetting_all else ()
    for origin, root in roots:
        try:
            validate_resource_location(path=root, context=context)
        except ValueError as error:
            diagnostics.append(HookDiagnostic(agent, origin, root, str(error), "error"))
            continue
        if not root.is_symlink() and not root.exists():
            continue
        entries.append(HookEntry(agent, origin, root, root.name, "plugin", "Remove plugin installation directory", "configured",
                                 HookRemoval(root, "directory", (), "delete")))
    for resource in resources:
        if resource.state == "missing":
            continue
        if any(resource.path.is_relative_to(root) for _origin, root in roots):
            continue
        if resource.kind == "configuration":
            inventory = configuration_cleanup(agent=agent, resource=resource, focuses=resource_focuses, context=context)
            entries.extend(inventory.entries)
            diagnostics.extend(inventory.diagnostics)
            continue
        if not resetting_all and resource.kind not in resource_focuses:
            continue
        if resource.path in configurations:
            continue
        if resource.kind == "hook":
            continue
        if resource.kind == "skill" and resource.state == "referenced":
            if not resetting_all:
                entries.append(HookEntry(agent, resource.origin, resource.path, resource.name, "skill",
                                         "External skill source: reset its configuration or supplying plugin registration", "referenced", None))
            continue
        if resource.kind == "plugin" and agent == "codex":
            continue
        if resource.kind == "plugin" and ("declared in" in resource.detail or "configured" in resource.detail.casefold()):
            continue
        target = resource.path
        linked_candidates = (target.parent, target) if resource.kind == "skill" and target.name == "SKILL.md" else (target,)
        try:
            for parent in linked_candidates:
                validate_resource_location(path=parent, context=context)
                if parent.is_symlink():
                    target = parent
                    break
        except ValueError as error:
            diagnostics.append(HookDiagnostic(agent, resource.origin, target, str(error), "error"))
            continue
        if not target.is_symlink() and not permitted_resource_path(path=target, home_directory=context.home_directory):
            diagnostics.append(HookDiagnostic(agent, resource.origin, target, "Protected resource excluded from cleanup", "error"))
            continue
        if not target.is_symlink() and not target.exists():
            diagnostics.append(HookDiagnostic(agent, resource.origin, resource.path, "Referenced resource is unavailable", "notice"))
            continue
        if not target.is_symlink() and resource.kind == "skill" and target.name == "SKILL.md":
            target = target.parent
        elif resource.kind == "plugin" and target.name in ("plugin.json", "package.json", "qwen-extension.json", "gemini-extension.json"):
            target = target.parent.parent if target.parent.name in (".codex-plugin", ".claude-plugin") else target.parent
        removal = (
            HookRemoval(target, "directory" if not target.is_symlink() and target.is_dir() else "file", (), "delete")
            if resource.origin in ("local", "global") else None
        )
        entries.append(HookEntry(agent, resource.origin, resource.path, resource.name, resource.kind, resource.detail, resource.state, removal))
    if "plugin" in resource_focuses and agent in ("pi", "omp", "opencode"):
        from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extensions import collect_extensions

        inventory = collect_extensions(agent=agent, context=context)
        entries.extend(inventory.entries)
        diagnostics.extend(inventory.diagnostics)
    return HookInventory(tuple(entries), tuple(diagnostics))
