"""Pure Python implementations for sessions commands - no typer dependencies."""

from pathlib import Path
from typing import Literal

from stackops.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
)
from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.cluster.sessions_managers.monitoring_types import StartResult
from stackops.utils.schemas.layouts.layout_types import LayoutConfig

BackendName = Literal["tmux", "herdr", "tuios"]


def select_layout(layouts_file: Path, selected_layouts_names: list[str], select_interactively: bool) -> list["LayoutConfig"]:
    """Select layout(s) from a layout file."""
    from stackops.utils.schemas.layouts.layout_file import read_layouts_file

    layouts = read_layouts_file(path=layouts_file)["layouts"]
    if len(layouts) == 0:
        raise ValueError(f"No layouts found in {layouts_file}")
    if len(selected_layouts_names) == 0:
        if not select_interactively:
            return layouts
        # options = [layout["layoutName"] for layout in layout_file["layouts"]]
        # from stackops.utils.options_utils.options import choose_from_options
        # selected_layouts_names = choose_from_options(multi=True, options=options, prompt="Choose a layout configuration:", tv=True, msg="Choose one option")
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
        from stackops.utils.schemas.yaml_document import yaml_document_text
        selected_layouts_names = choose_from_dict_with_preview(
            {layout["layoutName"]: yaml_document_text(document=layout) for layout in layouts},
            extension="yaml",
            multi=True,
            preview_size_percent=40,
        )

    print(f"Selected layout(s): {selected_layouts_names}")
    layouts_chosen: list[LayoutConfig] = []
    for name in selected_layouts_names:
        layout_chosen = next((layout for layout in layouts if layout["layoutName"] == name), None)
        if layout_chosen is None:
            layout_chosen = next((layout for layout in layouts if layout["layoutName"].lower() == name.lower()), None)
        if layout_chosen is None:
            available_layouts = [layout["layoutName"] for layout in layouts]
            raise ValueError(f"Layout '{name}' not found. Available layouts: {available_layouts}")
        layouts_chosen.append(layout_chosen)
    return layouts_chosen

def find_layout_file(layout_path: str) -> str:
    path_obj = Path(layout_path).expanduser().absolute()
    if not path_obj.exists():
        raise ValueError(f"""Layout file does not exist: {path_obj}""")
    if not path_obj.is_file():
        raise ValueError(f"""Layout path is not a file: {path_obj}""")
    return str(path_obj)


def run_layouts(
    sleep_inbetween: float,
    monitor: bool,
    parallel_layouts: int | None,
    kill_upon_completion: bool,
    backend: BackendName,
    on_conflict: SessionConflictAction,
    exit_mode: SessionExitMode,
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
        case "tmux":
            from stackops.cluster.sessions_managers.tmux.tmux_local_manager import TmuxLocalManager
            for i, a_layouts in enumerate(iterable):
                tmux_manager = TmuxLocalManager(
                    session_layouts=a_layouts,
                    session_name_prefix=None,
                    exit_mode=exit_mode,
                )
                start_results = tmux_manager.start_all_sessions(on_conflict=on_conflict)
                raise_on_failed_start(start_results, "tmux")
                if monitor:
                    tmux_manager.run_monitoring_routine(wait_ms=2000)
                    if kill_upon_completion:
                        tmux_manager.kill_all_sessions()
                if i < len(iterable) - 1:
                    time.sleep(sleep_inbetween)
        case "herdr":
            if monitor_requested:
                raise ValueError("--monitor is not supported by the Herdr backend.")
            if parallel_layouts is not None:
                raise ValueError("--parallel-layouts is not supported by the Herdr backend.")
            if kill_upon_completion:
                raise ValueError("--kill-upon-completion is not supported by the Herdr backend.")
            if exit_mode != "backToShell":
                raise ValueError("--exit is not supported by the Herdr backend; use back-to-shell.")
            from stackops.scripts.python.helpers.helpers_sessions.sessions_herdr import (
                run_layouts_with_herdr,
            )
            for i, a_layouts in enumerate(iterable):
                start_results = run_layouts_with_herdr(
                    layouts_selected=a_layouts,
                    on_conflict=on_conflict,
                )
                raise_on_failed_start(start_results, "Herdr")
                if i < len(iterable) - 1:
                    time.sleep(sleep_inbetween)
        case "tuios":
            from stackops.cluster.sessions_managers.session_conflict import kill_existing_session
            from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios import (
                monitor_launched_windows,
                run_layouts_with_tuios,
            )

            for i, a_layouts in enumerate(iterable):
                start_results, launched_windows = run_layouts_with_tuios(
                    layouts_selected=a_layouts,
                    on_conflict=on_conflict,
                    exit_mode=exit_mode,
                )
                raise_on_failed_start(start_results, "TUIOS")
                if monitor or kill_upon_completion:
                    monitor_launched_windows(launched_windows=launched_windows, poll_seconds=2.0)
                    if kill_upon_completion:
                        for session_name in launched_windows:
                            kill_existing_session("tuios", session_name)
                if i < len(iterable) - 1:
                    time.sleep(sleep_inbetween)
        case _:
            raise ValueError(f"Unsupported backend: {backend}")
