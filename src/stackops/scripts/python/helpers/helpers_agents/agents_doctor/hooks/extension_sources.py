from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files, permitted_hook_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import ConfigFormat, load_config_mapping


def read_extension_config(*, path: Path, context: DoctorContext, config_format: ConfigFormat) -> dict[str, object] | str | None:
    try:
        if not permitted_hook_path(path=path, context=context):
            return "Protected dotfiles path was excluded; coverage is incomplete."
        if not path.exists():
            return None
        return load_config_mapping(path=path, config_format=config_format)
    except OSError as error:
        return str(error)


def collect_auto_extensions(*, agent: DoctorAgent, origin: DoctorOrigin, directory: Path, context: DoctorContext) -> HookInventory:
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    children = hook_directory_files(directory=directory, context=context)
    if isinstance(children, str):
        return HookInventory((), (HookDiagnostic(agent, origin, directory, children, "error"),))
    for child in children:
        if child.name.startswith("."):
            continue
        if not permitted_hook_path(path=child, context=context):
            diagnostics.append(HookDiagnostic(agent, origin, child, "Protected extension path was excluded.", "error"))
            continue
        if child.is_file() and child.suffix in (".js", ".ts"):
            removal = HookRemoval(child, "file", (), "delete")
        elif child.is_dir():
            candidates = (child / "index.ts", child / "index.js", child / "package.json")
            if not any(permitted_hook_path(path=path, context=context) and path.is_file() for path in candidates):
                continue
            removal = HookRemoval(child, "directory", (), "delete")
        else:
            continue
        entries.append(HookEntry(agent, origin, child, child.stem, "extension lifecycle (dynamic)", str(child), "configured", removal))
    return HookInventory(tuple(entries), tuple(diagnostics))
