"""Pure Python implementations for sessions commands - no typer dependencies."""

import json
from pathlib import Path
from typing import Literal

from machineconfig.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
    kill_existing_session,
    list_existing_sessions,
    session_exists,
    validate_session_conflict_action,
)
from machineconfig.cluster.sessions_managers.zellij.zellij_utils.monitoring_types import StartResult

BackendName = Literal["zellij", "windows-terminal", "tmux"]


def select_layout(layouts_json_file: str, selected_layouts_names: list[str], select_interactively: bool) -> list["LayoutConfig"]:
    """Select layout(s) from a layout file."""
    from machineconfig.utils.schemas.layouts.layout_types import LayoutsFile
    json_str = Path(layouts_json_file).read_text(encoding="utf-8")
    try:
        layout_file: LayoutsFile = json.loads(json_str)
    except Exception:
        print(f"Failed to parse the json file {layouts_json_file}, trying to clean the comments and giving it another shot ... ")
        from machineconfig.utils.io import remove_c_style_comments
        json_str = remove_c_style_comments(json_str)
        layout_file = json.loads(json_str)
    if len(layout_file["layouts"]) == 0:
        raise ValueError(f"No layouts found in {layouts_json_file}")
    if len(selected_layouts_names) == 0:
        if not select_interactively:
            return layout_file["layouts"]
        # options = [layout["layoutName"] for layout in layout_file["layouts"]]
        # from machineconfig.utils.options import choose_from_options
        # selected_layouts_names = choose_from_options(multi=True, options=options, prompt="Choose a layout configuration:", tv=True, msg="Choose one option")
        from machineconfig.utils.options_utils.tv_options import choose_from_dict_with_preview
        selected_layouts_names = choose_from_dict_with_preview(
            {layout["layoutName"]: json.dumps(layout, indent=4) for layout in layout_file["layouts"]},
            extension="json",
            multi=True,
            preview_size_percent=40,
        )

    print(f"Selected layout(s): {selected_layouts_names}")
    layouts_chosen: list[LayoutConfig] = []
    for name in selected_layouts_names:
        layout_chosen = next((layout for layout in layout_file["layouts"] if layout["layoutName"] == name), None)
        if layout_chosen is None:
            layout_chosen = next((layout for layout in layout_file["layouts"] if layout["layoutName"].lower() == name.lower()), None)
        if layout_chosen is None:
            available_layouts = [layout["layoutName"] for layout in layout_file["layouts"]]
            raise ValueError(f"Layout '{name}' not found. Available layouts: {available_layouts}")
        layouts_chosen.append(layout_chosen)
    return layouts_chosen

def find_layout_file(layout_path: str) -> str:
    """Find layout file from a path."""
    from machineconfig.utils.path_helper import search_for_files_of_interest, match_file_name, sanitize_path
    from machineconfig.utils.options import choose_from_options
    path_obj = sanitize_path(layout_path)
    if not path_obj.exists():
        choice_file = match_file_name(sub_string=layout_path, search_root=Path.cwd(), suffixes={".json"})
    elif path_obj.is_dir():
        print(f"🔍 Searching recursively for Python, PowerShell and Shell scripts in directory `{path_obj}`")
        files = search_for_files_of_interest(path_obj, suffixes={".py", ".sh", ".ps1"})
        print(f"🔍 Got #{len(files)} results.")
        selected_file = choose_from_options(multi=False, options=files, tv=True, msg="Choose one option")
        if selected_file is None:
            raise FileNotFoundError("No layout file selected.")
        choice_file = Path(selected_file).expanduser().absolute()
    else:
        choice_file = path_obj
    return str(choice_file)


def _session_name_for_layout(layout_name: str, backend: BackendName) -> str:
    if backend in {"zellij", "tmux"}:
        name_core = layout_name.replace(" ", "_")
    else:
        name_core = layout_name
    if backend == "zellij":
        return f"LocalJobMgr_{name_core}"
    return name_core


def _resolve_conflicts_for_batch(
    layouts_batch: list["LayoutConfig"],
    backend: BackendName,
    on_conflict: SessionConflictAction,
) -> tuple[list["LayoutConfig"], set[str]]:
    existing_sessions = list_existing_sessions(backend)
    reserved_sessions = set(existing_sessions)
    layouts_to_run: list["LayoutConfig"] = []
    sessions_to_restart: set[str] = set()

    for layout in layouts_batch:
        original_layout_name = layout["layoutName"]
        target_session_name = _session_name_for_layout(original_layout_name, backend)
        conflict_with_existing = session_exists(target_session_name, existing_sessions, backend)
        conflict_with_reserved = session_exists(target_session_name, reserved_sessions, backend)

        if conflict_with_reserved:
            if on_conflict == "error":
                if conflict_with_existing:
                    raise ValueError(
                        f"Session '{target_session_name}' already exists. "
                        "Use --on-conflict restart or --on-conflict rename."
                    )
                raise ValueError(
                    f"Duplicate target session '{target_session_name}' detected in the selected layouts. "
                    "Use unique layout names or --on-conflict rename."
                )

            if on_conflict == "restart":
                if conflict_with_existing and target_session_name in sessions_to_restart:
                    raise ValueError(
                        f"Duplicate target session '{target_session_name}' detected in the selected layouts. "
                        "Use unique layout names or --on-conflict rename."
                    )
                if not conflict_with_existing:
                    raise ValueError(
                        f"Duplicate target session '{target_session_name}' detected in the selected layouts. "
                        "Use unique layout names or --on-conflict rename."
                    )
                print(
                    f"♻️ Restarting existing session '{target_session_name}' "
                    f"for layout '{original_layout_name}'."
                )
                sessions_to_restart.add(target_session_name)

            if on_conflict == "rename":
                suffix = 1
                renamed_layout_name = original_layout_name
                while True:
                    candidate_layout_name = f"{original_layout_name}_{suffix}"
                    candidate_session_name = _session_name_for_layout(candidate_layout_name, backend)
                    if not session_exists(candidate_session_name, reserved_sessions, backend):
                        renamed_layout_name = candidate_layout_name
                        target_session_name = candidate_session_name
                        break
                    suffix += 1
                print(
                    f"📝 Renaming layout '{original_layout_name}' to '{renamed_layout_name}' "
                    f"to avoid session conflict."
                )
                renamed_layout: "LayoutConfig" = {
                    "layoutName": renamed_layout_name,
                    "layoutTabs": layout["layoutTabs"],
                }
                layout = renamed_layout

        layouts_to_run.append(layout)
        reserved_sessions.add(target_session_name)

    return layouts_to_run, sessions_to_restart


def run_layouts(
    sleep_inbetween: float,
    monitor: bool,
    parallel_layouts: int | None,
    kill_upon_completion: bool,
    backend: BackendName,
    on_conflict: SessionConflictAction,
    layouts_selected: list["LayoutConfig"],
) -> None:
    """Launch terminal sessions based on a layout configuration file."""
    import time
    monitor_requested = monitor
    monitor = monitor or (parallel_layouts is not None)
    if parallel_layouts is not None and not monitor_requested:
        print("Note: --parallel-layouts implies --monitor; waiting for each batch to finish before launching the next one.")
    if parallel_layouts is not None and parallel_layouts <= 0:
        raise ValueError("parallel_layouts must be a positive integer when provided")
    validate_session_conflict_action(on_conflict)

    if parallel_layouts is None:
        iterable: list[list["LayoutConfig"]] = [layouts_selected]
    else:
        iterable = [layouts_selected[index:index + parallel_layouts] for index in range(0, len(layouts_selected), parallel_layouts)]

    def raise_on_failed_start(start_results: dict[str, StartResult], backend_name: str) -> None:
        failures = {name: result for name, result in start_results.items() if not result.get("success", False)}
        if failures:
            details = "; ".join(f"{name}: {result.get('error', 'unknown error')}" for name, result in failures.items())
            raise ValueError(f"{backend_name} session start failure(s): {details}")
    match backend:
        case "zellij":
            from machineconfig.cluster.sessions_managers.zellij.zellij_local_manager import ZellijLocalManager
            for i, a_layouts in enumerate(iterable):
                manager = ZellijLocalManager(session_layouts=a_layouts)
                start_results = manager.start_all_sessions(on_conflict=on_conflict, poll_interval=2, poll_seconds=10)
                raise_on_failed_start(start_results, "Zellij")
                if monitor:
                    manager.run_monitoring_routine(wait_ms=2000)
                    if kill_upon_completion:
                        manager.kill_all_sessions()
                if i < len(iterable) - 1:
                    time.sleep(sleep_inbetween)
        case "windows-terminal":
            from machineconfig.cluster.sessions_managers.windows_terminal.wt_local_manager import WTLocalManager
            for i, a_layouts in enumerate(iterable):
                layouts_to_run, sessions_to_restart = _resolve_conflicts_for_batch(a_layouts, backend, on_conflict)
                if on_conflict == "restart":
                    for session_name in sorted(sessions_to_restart):
                        kill_existing_session(backend, session_name)
                if len(layouts_to_run) == 0:
                    print("No layouts to launch for this batch after conflict resolution.")
                    if i < len(iterable) - 1:
                        time.sleep(sleep_inbetween)
                    continue
                wt_manager = WTLocalManager(session_layouts=layouts_to_run, session_name_prefix=None)
                start_results = wt_manager.start_all_sessions()
                raise_on_failed_start(start_results, "Windows Terminal")
                if monitor:
                    wt_manager.run_monitoring_routine(wait_ms=2000)
                    if kill_upon_completion:
                        wt_manager.kill_all_sessions()
                if i < len(iterable) - 1:
                    time.sleep(sleep_inbetween)
        case "tmux":
            from machineconfig.cluster.sessions_managers.tmux.tmux_local_manager import TmuxLocalManager
            for i, a_layouts in enumerate(iterable):
                tmux_manager = TmuxLocalManager(session_layouts=a_layouts, session_name_prefix=None)
                start_results = tmux_manager.start_all_sessions(on_conflict=on_conflict)
                raise_on_failed_start(start_results, "tmux")
                if monitor:
                    tmux_manager.run_monitoring_routine(wait_ms=2000)
                    if kill_upon_completion:
                        tmux_manager.kill_all_sessions()
                if i < len(iterable) - 1:
                    time.sleep(sleep_inbetween)
        case _:
            raise ValueError(f"Unsupported backend: {backend}")


if __name__ == "__main__":
    from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig
    _ = LayoutConfig
