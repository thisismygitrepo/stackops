from pathlib import Path

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    interactive_choose_with_preview,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import (
    classify_pane_status,
    list_session_names,
    run_command,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import (
    build_preview,
    collect_session_snapshot,
)
from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TMUX_EXPORT_DEFAULT_FILENAME,
    TMUX_EXPORT_LAYOUT_VERSION,
    TMUX_EXPORT_SHELL_COMMAND,
    TmuxExportCommandSource,
)
from stackops.utils.schemas.layouts.layout_types import (
    LayoutConfig,
    LayoutFileWriteMode,
    TabConfig,
    serialize_layouts_to_file,
)


def _parse_session_names(session_names: str) -> list[str]:
    parsed_names = [
        token.strip()
        for token in session_names.split(",")
        if token.strip()
    ]
    if len(parsed_names) == 0:
        raise ValueError("No tmux sessions were provided.")
    return list(dict.fromkeys(parsed_names))


def _validate_requested_sessions(requested_sessions: list[str], available_sessions: list[str]) -> None:
    available_session_set = set(available_sessions)
    missing_sessions = [
        session_name
        for session_name in requested_sessions
        if session_name not in available_session_set
    ]
    if len(missing_sessions) == 0:
        return
    raise ValueError(
        f"Unknown tmux session(s): {missing_sessions}. "
        f"Available sessions: {available_sessions}"
    )


def _choose_tmux_sessions_interactively(available_sessions: list[str]) -> list[str]:
    options_to_preview_mapping = {
        session_name: build_preview(
            session_name=session_name,
            run_command_fn=run_command,
            classify_pane_status_fn=classify_pane_status,
        )
        for session_name in available_sessions
    }
    selected_sessions = interactive_choose_with_preview(
        msg="Choose tmux sessions to export:",
        options_to_preview_mapping=options_to_preview_mapping,
        multi=True,
    )
    if len(selected_sessions) == 0:
        raise ValueError("No tmux sessions selected.")
    return selected_sessions


def resolve_tmux_session_names_for_export(
    session_names: str | None,
    export_all_sessions: bool,
) -> list[str]:
    available_sessions = list_session_names()
    if len(available_sessions) == 0:
        raise ValueError("No tmux sessions are available to export.")
    if export_all_sessions and session_names is not None:
        raise ValueError("--all cannot be used together with --sessions.")
    if export_all_sessions:
        return available_sessions
    if session_names is None or session_names == "":
        return _choose_tmux_sessions_interactively(available_sessions=available_sessions)
    requested_sessions = _parse_session_names(session_names=session_names)
    _validate_requested_sessions(
        requested_sessions=requested_sessions,
        available_sessions=available_sessions,
    )
    return requested_sessions


def _select_representative_pane(
    window: dict[str, str],
    panes_by_window: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    window_panes = panes_by_window.get(window["window_index"], [])
    for pane in window_panes:
        if pane["pane_active"]:
            return pane
    if len(window_panes) == 0:
        return None
    return window_panes[0]


def _command_from_pane(
    pane: dict[str, str] | None,
    command_source: TmuxExportCommandSource,
) -> str:
    if pane is None:
        return TMUX_EXPORT_SHELL_COMMAND
    match command_source:
        case "shell":
            return TMUX_EXPORT_SHELL_COMMAND
        case "current-command":
            command = pane.get("pane_command", "").strip()
        case "start-command":
            command = pane.get("pane_start_command", "").strip()
    if command == "":
        return TMUX_EXPORT_SHELL_COMMAND
    return command


def _start_dir_from_pane(pane: dict[str, str] | None) -> str:
    if pane is None:
        return str(Path.home())
    pane_cwd = pane.get("pane_cwd", "").strip()
    if pane_cwd == "":
        return str(Path.home())
    return pane_cwd


def _unique_tab_name(window: dict[str, str], used_tab_names: set[str]) -> str:
    window_name = window["window_name"].strip()
    if window_name == "":
        window_name = f"window-{window['window_index']}"
    if window_name not in used_tab_names:
        used_tab_names.add(window_name)
        return window_name

    indexed_window_name = f"{window['window_index']}-{window_name}"
    if indexed_window_name not in used_tab_names:
        used_tab_names.add(indexed_window_name)
        return indexed_window_name

    suffix = 2
    while True:
        candidate_name = f"{indexed_window_name}-{suffix}"
        if candidate_name not in used_tab_names:
            used_tab_names.add(candidate_name)
            return candidate_name
        suffix += 1


def _build_layout_for_tmux_session(
    session_name: str,
    command_source: TmuxExportCommandSource,
) -> LayoutConfig:
    windows, panes_by_window, pane_warning = collect_session_snapshot(
        session_name=session_name,
        run_command_fn=run_command,
    )
    if windows is None:
        detail = pane_warning or "No tmux window data available."
        raise ValueError(f"Unable to inspect tmux session '{session_name}': {detail}")
    if len(windows) == 0:
        raise ValueError(f"Tmux session '{session_name}' has no windows to export.")

    used_tab_names: set[str] = set()
    tabs: list[TabConfig] = []
    for window in windows:
        representative_pane = _select_representative_pane(
            window=window,
            panes_by_window=panes_by_window,
        )
        tabs.append(
            {
                "tabName": _unique_tab_name(
                    window=window,
                    used_tab_names=used_tab_names,
                ),
                "startDir": _start_dir_from_pane(pane=representative_pane),
                "command": _command_from_pane(
                    pane=representative_pane,
                    command_source=command_source,
                ),
            }
        )
    return {"layoutName": session_name, "layoutTabs": tabs}


def build_layouts_from_tmux_sessions(
    session_names: list[str],
    command_source: TmuxExportCommandSource,
) -> list[LayoutConfig]:
    if len(session_names) == 0:
        raise ValueError("No tmux sessions were selected for export.")
    return [
        _build_layout_for_tmux_session(
            session_name=session_name,
            command_source=command_source,
        )
        for session_name in session_names
    ]


def resolve_export_output_path(output_path: str | None) -> Path:
    if output_path is None:
        return Path.cwd().joinpath(TMUX_EXPORT_DEFAULT_FILENAME).absolute()
    return Path(output_path).expanduser().absolute()


def write_exported_layouts(
    layouts: list[LayoutConfig],
    output_path: Path,
    overwrite: bool,
    merge: bool,
) -> None:
    if overwrite and merge:
        raise ValueError("--overwrite cannot be used together with --merge.")
    if output_path.exists() and not overwrite and not merge:
        raise ValueError(
            f"Output file already exists: {output_path}. "
            "Use --overwrite to replace it or --merge to update matching layout names."
        )
    write_mode: LayoutFileWriteMode = "merge_by_layout_name" if merge else "replace_file"
    serialize_layouts_to_file(
        layouts=layouts,
        version=TMUX_EXPORT_LAYOUT_VERSION,
        path=str(output_path),
        write_mode=write_mode,
    )


def export_tmux_sessions(
    session_names: str | None,
    export_all_sessions: bool,
    output_path: str | None,
    overwrite: bool,
    merge: bool,
    command_source: TmuxExportCommandSource,
) -> Path:
    resolved_session_names = resolve_tmux_session_names_for_export(
        session_names=session_names,
        export_all_sessions=export_all_sessions,
    )
    layouts = build_layouts_from_tmux_sessions(
        session_names=resolved_session_names,
        command_source=command_source,
    )
    resolved_output_path = resolve_export_output_path(output_path=output_path)
    write_exported_layouts(
        layouts=layouts,
        output_path=resolved_output_path,
        overwrite=overwrite,
        merge=merge,
    )
    return resolved_output_path
