import os
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_config import config_entries
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.opencode_config import config_paths
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extension_sources import collect_auto_extensions, read_extension_config
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.omp_hooks import collect_omp_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin, DoctorResourceState
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import ConfigFormat


def _configured_extensions(
    *, agent: DoctorAgent, origin: DoctorOrigin, path: Path, config_format: ConfigFormat, context: DoctorContext
) -> HookInventory:
    mapping = read_extension_config(path=path, context=context, config_format=config_format)
    if mapping is None:
        return HookInventory((), ())
    if isinstance(mapping, str):
        return HookInventory((), (HookDiagnostic(agent, origin, path, mapping, "error"),))
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    keys = ("plugin", "plugins") if agent == "opencode" else ("extensions", "packages") if agent == "pi" else ("extensions",)
    for key in keys:
        if key not in mapping:
            continue
        values = mapping[key]
        if not isinstance(values, list):
            diagnostics.append(HookDiagnostic(agent, origin, path, f"""{key} must contain an array.""", "error"))
            continue
        for index, value in enumerate(cast(list[object], values)):
            state: DoctorResourceState = "configured"
            if isinstance(value, str):
                name = value
                if value.startswith(("!", "-")):
                    state = "disabled"
            elif isinstance(value, dict):
                declaration = cast(dict[str, object], value)
                raw_name = declaration.get("source") if agent == "pi" else declaration.get("package")
                if not isinstance(raw_name, str):
                    diagnostics.append(HookDiagnostic(agent, origin, path, f"""Invalid {key} entry at index {index}.""", "error"))
                    continue
                name = raw_name
                if declaration.get("extensions") == [] or declaration.get("enabled") is False or declaration.get("autoload") is False:
                    state = "disabled"
            else:
                diagnostics.append(HookDiagnostic(agent, origin, path, f"""Invalid {key} entry at index {index}.""", "error"))
                continue
            removal = HookRemoval(path, config_format, (key, index), "delete")
            entries.append(HookEntry(agent, origin, path, name, "extension lifecycle (dynamic)", name, state, removal))
    return HookInventory(tuple(entries), tuple(diagnostics))


def collect_extensions(*, agent: DoctorAgent, context: DoctorContext) -> HookInventory:
    configs: list[tuple[DoctorOrigin, Path, ConfigFormat]] = []
    directories: list[tuple[DoctorOrigin, Path]] = []
    match agent:
        case "pi":
            roots: tuple[tuple[DoctorOrigin, Path], ...] = (("global", context.pi_home), ("local", context.working_directory / ".pi"))
            configs.extend((origin, root / "settings.json", "json") for origin, root in roots)
            directories.extend((origin, root / "extensions") for origin, root in roots)
        case "omp":
            configs.extend(config_entries(context=context))
            directories.extend((("global", context.omp_home / "extensions"), ("local", context.working_directory / ".omp" / "extensions")))
        case "opencode":
            configs.extend((origin, path, "json") for origin, path in config_paths(context=context))
            directories.append(("global", context.xdg_config_directory / "opencode" / "plugins"))
            directories.extend(("local", directory / ".opencode" / "plugins") for directory in context.ancestor_directories)
            custom = os.environ.get("OPENCODE_CONFIG")
            if custom:
                path = Path(custom).expanduser()
                configs.append(("global", path if path.is_absolute() else context.working_directory / path, "json"))
            custom_directory = os.environ.get("OPENCODE_CONFIG_DIR")
            if custom_directory:
                root = Path(custom_directory).expanduser()
                if not root.is_absolute():
                    root = context.working_directory / root
                configs.extend(("global", root / filename, "json") for filename in ("opencode.json", "opencode.jsonc"))
                directories.append(("global", root / "plugins"))
        case _:
            return HookInventory((), ())
    inventories = [
        _configured_extensions(agent=agent, origin=origin, path=path, config_format=config_format, context=context)
        for origin, path, config_format in dict.fromkeys(configs)
    ]
    inventories.extend(
        collect_auto_extensions(agent=agent, origin=origin, directory=directory, context=context) for origin, directory in dict.fromkeys(directories)
    )
    if agent == "omp":
        inventories.append(collect_omp_hooks(context=context))
    notice = HookDiagnostic(
        agent,
        "local",
        context.working_directory,
        "Executable extensions can register hooks dynamically; removing an entry removes the whole extension or package. Session CLI/SDK injections are not inventoried.",
        "notice",
    )
    return HookInventory(
        tuple(entry for inventory in inventories for entry in inventory.entries),
        (*tuple(diagnostic for inventory in inventories for diagnostic in inventory.diagnostics), notice),
    )
