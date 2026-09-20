import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval, HookSelector
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResourceFocus


@dataclass(frozen=True)
class DeepSeekPatchEntry:
    name: str
    module: str
    selector: HookSelector
    disabled: bool


def deepseek_home(*, context: DoctorContext) -> Path:
    configured = os.environ.get("DSH_HOME")
    if configured is None or not configured.strip():
        return context.home_directory / ".dsh"
    path = Path(configured).expanduser()
    return path if path.is_absolute() else context.working_directory / path


def deepseek_patch_paths(*, context: DoctorContext) -> tuple[tuple[DoctorOrigin, Path], ...]:
    home = deepseek_home(context=context)
    paths: list[tuple[DoctorOrigin, Path]] = [("global", home / "cordis.patch.yml")]
    profiles = home / "profiles"
    if permitted_resource_path(path=profiles, home_directory=context.home_directory) and profiles.is_dir():
        for profile in sorted(profiles.iterdir()):
            if profile.name == "node_modules" or not permitted_resource_path(path=profile, home_directory=context.home_directory):
                continue
            if profile.is_dir():
                paths.append(("global", profile / "cordis.patch.yml"))
    paths.append(("local", context.project_root / ".dsh" / "cordis.patch.yml"))
    return tuple(paths)


def patch_entries(*, node: Node, selector: HookSelector, disabled: bool) -> tuple[DeepSeekPatchEntry, ...]:
    if not isinstance(node, SequenceNode):
        raise ValueError("DeepSeek patch entries must be a YAML sequence")
    entries: list[DeepSeekPatchEntry] = []
    for index, item in enumerate(node.value):
        if not isinstance(item, MappingNode):
            raise ValueError("DeepSeek patch entries must be mappings")
        mapping = {key.value: value for key, value in item.value if isinstance(key, ScalarNode)}
        location = (*selector, index)
        disabled_node = mapping.get("disabled")
        is_disabled = disabled or isinstance(disabled_node, ScalarNode) and disabled_node.value.lower() == "true"
        inserted = mapping.get("insert")
        if inserted is not None:
            entries.extend(patch_entries(node=inserted, selector=(*location, "insert"), disabled=is_disabled))
            continue
        group = mapping.get("group")
        config = mapping.get("config")
        if isinstance(group, ScalarNode) and group.value.lower() == "true" and isinstance(config, SequenceNode):
            entries.extend(patch_entries(node=config, selector=(*location, "config"), disabled=is_disabled))
            continue
        module = mapping.get("name")
        identifier = mapping.get("id")
        module_name = module.value if isinstance(module, ScalarNode) else ""
        name = identifier.value if isinstance(identifier, ScalarNode) else module_name
        if name:
            entries.append(DeepSeekPatchEntry(name, module_name, location, is_disabled))
    return tuple(entries)


def deepseek_patch_inventory(
    *, context: DoctorContext, paths: tuple[tuple[DoctorOrigin, Path], ...], focuses: tuple[DoctorResourceFocus, ...],
) -> HookInventory:
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    for origin, path in paths:
        if not permitted_resource_path(path=path, home_directory=context.home_directory):
            diagnostics.append(HookDiagnostic("deepseek", origin, path, "Protected configuration excluded from inspection", "error"))
            continue
        try:
            if not path.is_file():
                continue
            node = yaml.compose(path.read_text(encoding="utf-8"))
            if node is None:
                continue
            declarations = patch_entries(node=node, selector=(), disabled=False)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
            diagnostics.append(HookDiagnostic("deepseek", origin, path, str(error), "error"))
            continue
        modules = {declaration.name: declaration.module for declaration in declarations if declaration.module}
        for declaration in declarations:
            module = declaration.module or modules.get(declaration.name, "")
            is_mcp = module == "@deepseek-ai/dsh-mcp-client"
            is_hook = module in ("@deepseek-ai/dsh-hooks-codex", "@deepseek-ai/dsh-hooks-claude-code")
            selected = "plugin" in focuses or "all" in focuses or is_mcp and "mcp" in focuses or is_hook and "hook" in focuses
            if not selected:
                continue
            entries.append(HookEntry(
                "deepseek", origin, path, declaration.name, "mcp" if is_mcp else "hook" if is_hook else "plugin",
                module or declaration.name, "disabled" if declaration.disabled else "configured",
                HookRemoval(path, "deepseek-yaml", declaration.selector, "delete"),
            ))
    return HookInventory(tuple(entries), tuple(diagnostics))
