from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import (
    HookDiagnostic,
    HookEntry,
    HookFormat,
    HookInventory,
    HookRemoval,
    HookSelector,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceFocus
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import load_config_mapping


def _selected_sections(
    *, mapping: dict[str, object], selector: HookSelector, focuses: tuple[DoctorResourceFocus, ...]
) -> list[tuple[str, HookSelector, object]]:
    sections: list[tuple[str, HookSelector, object]] = []
    for key, value in mapping.items():
        location = (*selector, key)
        kind: str | None = None
        if key in ("mcp", "mcpServers", "mcp_servers") and ("mcp" in focuses or "all" in focuses):
            kind = "mcp"
        elif key in ("plugins", "plugin", "enabledPlugins", "extensions", "packages") and "plugin" in focuses:
            kind = "plugin"
        elif key in ("instructions", "systemPrompt", "system_prompt") and "instructions" in focuses:
            kind = "instructions"
        elif key in ("skills", "skills.customDirectories") and "skill" in focuses:
            kind = "skill"
        if kind is not None:
            if isinstance(value, dict):
                sections.extend((kind, (*location, name), entry) for name, entry in cast(dict[str, object], value).items())
            elif isinstance(value, list):
                sections.extend((kind, (*location, index), entry) for index, entry in enumerate(cast(list[object], value)))
            else:
                sections.append((kind, location, value))
        elif isinstance(value, dict):
            sections.extend(_selected_sections(mapping=cast(dict[str, object], value), selector=location, focuses=focuses))
    return sections


def configuration_cleanup(
    *, agent: DoctorAgent, resource: DoctorResource, focuses: tuple[DoctorResourceFocus, ...], context: DoctorContext,
) -> HookInventory:
    path = resource.path
    if path.suffix in (".yml", ".yaml"):
        config_format = "yaml"
    elif path.suffix == ".toml":
        config_format = "toml"
    else:
        config_format = "json"
    full_reset = "all" in focuses or "configuration" in focuses
    preserves_state = agent == "claude" and path.name == ".claude.json"
    if full_reset and not preserves_state:
        removal = HookRemoval(path, "file", (), "delete") if resource.origin in ("local", "global") else None
        entry = HookEntry(agent, resource.origin, path, resource.name, "configuration", "Reset configuration file", resource.state, removal)
        return HookInventory((entry,), ())
    mapping = load_config_mapping(path=path, config_format=config_format)
    if isinstance(mapping, str):
        return HookInventory((), (HookDiagnostic(agent, resource.origin, path, mapping, "error"),))
    sections: list[tuple[DoctorOrigin, str, HookSelector, object]] = []
    selected_mapping = {"mcpServers": mapping["mcpServers"]} if preserves_state and "mcpServers" in mapping else {} if preserves_state else mapping
    sections.extend((resource.origin, kind, selector, value) for kind, selector, value in _selected_sections(mapping=selected_mapping, selector=(), focuses=focuses))
    projects = mapping.get("projects") if preserves_state else None
    if isinstance(projects, dict):
        project_settings = cast(dict[str, object], projects)
        for directory in context.ancestor_directories:
            project = project_settings.get(str(directory))
            if isinstance(project, dict):
                sections.extend(("local", kind, selector, value) for kind, selector, value in _selected_sections(
                    mapping=cast(dict[str, object], project), selector=("projects", str(directory)), focuses=focuses,
                ))
    entries: list[HookEntry] = []
    for origin, kind, selector, value in sections:
        name = str(selector[-1])
        command = " / ".join(str(part) for part in selector)
        if isinstance(value, str):
            name = value
        elif isinstance(value, dict):
            details = cast(dict[str, object], value)
            source = details.get("source", details.get("package"))
            if isinstance(source, str):
                name = source
            executable = details.get("command")
            if isinstance(executable, str):
                command = f"""{command}: {executable}"""
        is_enabled_plugin = len(selector) > 1 and selector[-2] == "enabledPlugins"
        removal_selector = selector
        action = "disable" if is_enabled_plugin else "delete"
        if agent == "codex" and kind == "plugin" and isinstance(value, dict):
            removal_selector = (*selector, "enabled")
            action = "disable"
        removal = (
            HookRemoval(path, cast(HookFormat, config_format), removal_selector, action)
            if origin in ("local", "global") else None
        )
        entries.append(HookEntry(
            agent, origin, path, name, kind,
            command, resource.state, removal,
        ))
    return HookInventory(tuple(entries), ())
