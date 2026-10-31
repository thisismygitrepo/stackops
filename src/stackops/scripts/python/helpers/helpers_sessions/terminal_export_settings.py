from dataclasses import dataclass
from typing import Literal, TypeAlias, cast, get_args

from stackops.scripts.python.helpers.helpers_sessions.terminal_export import (
    TerminalExportBackend,
    TerminalExportBackendOption,
    resolve_export_backend,
    supported_command_sources,
)
from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TERMINAL_EXPORT_DEFAULT_COMMAND_SOURCE,
    TmuxExportCommandSource,
)

ExportWriteMode: TypeAlias = Literal["merge", "overwrite"]


@dataclass(frozen=True, slots=True)
class TerminalExportSettings:
    backend: TerminalExportBackend
    command_source: TmuxExportCommandSource
    overwrite: bool
    merge: bool


def _backend_session_names(backend: TerminalExportBackend) -> list[str]:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names

            return list_session_names()
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions.herdr_export_source import (
                list_workspace_entries,
                workspace_display_name,
            )

            return [workspace_display_name(workspace) for workspace in list_workspace_entries()]
        case "tuios":
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_session_entries

            return [session.name for session in list_session_entries() if not session.saved]


def _describe_backend(backend: TerminalExportBackend) -> str:
    import shutil

    if shutil.which(backend) is None:
        return "⛔ not installed"
    try:
        session_names = _backend_session_names(backend=backend)
    except ValueError as error:
        return f"""⚠️ unavailable: {str(error).partition("\n")[0]}"""
    if not session_names:
        return "💤 no running sessions"
    return f"""✅ sessions: {len(session_names)} · {", ".join(session_names)}"""


def _choose[T: str](choices: dict[str, T], msg: str) -> T:
    from stackops.utils.options_utils.options import choose_from_options

    selection = choose_from_options(options=list(choices), msg=msg, multi=False, custom_input=False, tv=True)
    if selection is None:
        raise ValueError("Nothing selected, export cancelled.")
    return choices[selection]


def _command_source_description(command_source: TmuxExportCommandSource) -> str:
    match command_source:
        case "shell":
            return "open a plain shell in every pane"
        case "current-command":
            return "rerun what each pane is running right now"
        case "start-command":
            return "rerun the command each pane was started with"


def resolve_terminal_export_settings(
    *,
    interactive: bool,
    backend: TerminalExportBackendOption | None,
    command_source: TmuxExportCommandSource | None,
    output_path: str | None,
    overwrite: bool,
    merge: bool,
) -> TerminalExportSettings:
    resolved_backend: TerminalExportBackend
    match backend:
        case None if interactive:
            backends = cast(tuple[TerminalExportBackend, ...], get_args(TerminalExportBackend))
            backend_choices: dict[str, TerminalExportBackend] = {f"""{name}  [{_describe_backend(backend=name)}]""": name for name in backends}
            resolved_backend = _choose(choices=backend_choices, msg="Choose a backend to export from:")
        case _:
            resolved_backend = resolve_export_backend(backend=backend)

    resolved_command_source: TmuxExportCommandSource
    match command_source:
        case None if interactive:
            allowed_command_sources = supported_command_sources(backend=resolved_backend)
            command_source_choices: dict[str, TmuxExportCommandSource] = {
                f"""{source}: {_command_source_description(command_source=source)}""": source for source in allowed_command_sources
            }
            resolved_command_source = (
                _choose(choices=command_source_choices, msg=f"""Choose what each exported {resolved_backend} pane should run:""")
                if len(command_source_choices) > 1
                else allowed_command_sources[0]
            )
        case None:
            resolved_command_source = TERMINAL_EXPORT_DEFAULT_COMMAND_SOURCE
        case _:
            resolved_command_source = command_source

    write_mode: ExportWriteMode | None = "overwrite" if overwrite else "merge" if merge else None
    if interactive and write_mode is None:
        from stackops.scripts.python.helpers.helpers_sessions.tmux_export import resolve_export_output_path

        resolved_output_path = resolve_export_output_path(output_path=output_path)
        if resolved_output_path.exists():
            write_mode_choices: dict[str, ExportWriteMode] = {
                "merge: replace layouts with matching names, keep the rest": "merge",
                "overwrite: replace the whole file": "overwrite",
            }
            write_mode = _choose(choices=write_mode_choices, msg=f"""Output file already exists: {resolved_output_path}""")
    return TerminalExportSettings(
        backend=resolved_backend,
        command_source=resolved_command_source,
        overwrite=overwrite or write_mode == "overwrite",
        merge=merge or write_mode == "merge",
    )
