import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files, permitted_hook_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResourceState


def collect_cline_hooks(*, context: DoctorContext) -> HookInventory:
    roots: tuple[tuple[DoctorOrigin, Path], ...] = (
        ("global", context.home_directory / "Documents/Cline/Hooks"),
        ("global", Path(os.environ.get("CLINE_HOOKS_DIR", str(context.home_directory / ".cline/hooks"))).expanduser()),
        ("local", context.project_root / ".clinerules/hooks"),
        ("local", context.project_root / ".cline/hooks"),
    )
    entries: list[HookEntry] = []
    diagnostics: list[HookDiagnostic] = []
    for origin, root in roots:
        paths = hook_directory_files(directory=root, context=context)
        if isinstance(paths, str):
            diagnostics.append(HookDiagnostic("cline", origin, root, paths, "error"))
            continue
        for path in paths:
            if not permitted_hook_path(path=path, context=context):
                diagnostics.append(HookDiagnostic("cline", origin, path, "Protected dotfiles hook was excluded.", "error"))
                continue
            if not path.is_file():
                continue
            state: DoctorResourceState = "configured" if os.access(path, os.X_OK) else "available"
            entries.append(HookEntry("cline", origin, path, path.name, path.stem, str(path), state, HookRemoval(path, "file", (), "delete")))
    return HookInventory(tuple(entries), tuple(diagnostics))
