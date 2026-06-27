from pathlib import Path
from typing import Literal, TypeAlias

from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TmuxExportCommandSource,
)

TerminalExportBackend: TypeAlias = Literal["tmux", "herdr"]
TerminalExportBackendOption: TypeAlias = Literal["tmux", "t", "herdr", "h"]


def resolve_export_backend(
    backend: TerminalExportBackendOption,
) -> TerminalExportBackend:
    import platform

    match backend:
        case "tmux" | "t":
            return "tmux"
        case "herdr" | "h":
            if platform.system().lower() == "windows":
                raise ValueError("Herdr export is not supported on Windows.")
            return "herdr"
        case _:
            raise ValueError(f"Unsupported export backend: {backend}")


def export_terminal_sessions(
    session_names: str | None,
    export_all_sessions: bool,
    output_path: str | None,
    overwrite: bool,
    merge: bool,
    command_source: TmuxExportCommandSource,
    backend: TerminalExportBackendOption,
) -> tuple[Path, TerminalExportBackend]:
    from stackops.scripts.python.helpers.helpers_sessions.herdr_export import (
        build_layouts_from_herdr_workspaces,
    )
    from stackops.scripts.python.helpers.helpers_sessions.herdr_export_selection import (
        resolve_herdr_workspaces_for_export,
    )
    from stackops.scripts.python.helpers.helpers_sessions.tmux_export import (
        build_layouts_from_tmux_sessions,
        resolve_export_output_path,
        resolve_tmux_session_names_for_export,
        write_exported_layouts,
    )

    resolved_backend = resolve_export_backend(backend=backend)
    match resolved_backend:
        case "tmux":
            resolved_session_names = resolve_tmux_session_names_for_export(
                session_names=session_names,
                export_all_sessions=export_all_sessions,
            )
            layouts = build_layouts_from_tmux_sessions(
                session_names=resolved_session_names,
                command_source=command_source,
            )
        case "herdr":
            if command_source != "shell":
                raise ValueError("Herdr export only supports --command-source shell.")
            resolved_workspaces = resolve_herdr_workspaces_for_export(
                workspace_names=session_names,
                export_all_workspaces=export_all_sessions,
            )
            layouts = build_layouts_from_herdr_workspaces(
                workspaces=resolved_workspaces,
                command_source=command_source,
            )
    resolved_output_path = resolve_export_output_path(output_path=output_path)
    write_exported_layouts(
        layouts=layouts,
        output_path=resolved_output_path,
        overwrite=overwrite,
        merge=merge,
    )
    return (resolved_output_path, resolved_backend)
