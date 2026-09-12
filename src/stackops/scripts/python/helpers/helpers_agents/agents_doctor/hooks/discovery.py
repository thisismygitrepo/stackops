from dataclasses import replace

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.claude_plugins import collect_claude_plugin_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.cline import collect_cline_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory import collect_hook_mapping
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import read_hook_mapping
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.sources import json_hook_sources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorResourceState


def collect_hooks(*, agent: DoctorAgent, context: DoctorContext) -> HookInventory:
    if agent == "codex":
        from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_hooks import collect_codex_hooks

        return collect_codex_hooks(context=context)
    if agent in ("pi", "omp", "opencode"):
        from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extensions import collect_extensions

        return collect_extensions(agent=agent, context=context)
    sources, source_diagnostics = json_hook_sources(agent=agent, context=context)
    entries: list[HookEntry] = []
    diagnostics = list(source_diagnostics)
    for source in sources:
        mapping = read_hook_mapping(path=source.path, context=context)
        if mapping is None:
            continue
        if isinstance(mapping, str):
            diagnostics.append(HookDiagnostic(agent, source.origin, source.path, mapping, "error"))
            continue
        state: DoctorResourceState = "configured"
        if agent == "droid" and source.path.name == "settings.json":
            standalone = read_hook_mapping(path=source.path.parent / "hooks.json", context=context)
            if standalone is not None:
                state = "shadowed"
        inventory = collect_hook_mapping(source=source, mapping=mapping, state=state, removal=None)
        entries.extend(inventory.entries)
        diagnostics.extend(inventory.diagnostics)
    if agent == "claude":
        plugins = collect_claude_plugin_hooks(context=context, sources=sources)
        entries.extend(plugins.entries)
        diagnostics.extend(plugins.diagnostics)
    if agent == "cline":
        scripts = collect_cline_hooks(context=context)
        entries.extend(scripts.entries)
        diagnostics.extend(scripts.diagnostics)
    if agent not in ("claude", "cursor-agent", "copilot", "droid", "qwen", "q", "cline"):
        diagnostics.append(
            HookDiagnostic(
                agent,
                "local",
                context.project_root,
                "No verified hook configuration adapter for this agent; absence of entries does not establish a clean setup.",
                "notice",
            )
        )
    else:
        diagnostics.append(
            HookDiagnostic(
                agent,
                "local",
                context.project_root,
                "Reports persisted hook declarations. Session flags, trust decisions, remote organization policies and hooks registered at runtime require inspection in the agent.",
                "notice",
            )
        )
    if agent in ("cursor-agent", "copilot", "droid", "qwen", "cline"):
        diagnostics.append(
            HookDiagnostic(
                agent,
                "global",
                context.home_directory,
                "Plugin and extension code can register additional hooks; inspect the plugin inventory as well.",
                "notice",
            )
        )
    unique_entries = tuple(dict.fromkeys(entries))
    if agent == "q":
        unique_entries = tuple(replace(entry, name=f"""{entry.path.stem}: {entry.name}""") for entry in unique_entries)
    return HookInventory(unique_entries, tuple(dict.fromkeys(diagnostics)))
