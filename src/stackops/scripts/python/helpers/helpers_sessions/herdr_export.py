from collections.abc import Iterable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_sessions.herdr_export_source import (
    JsonObject,
    entry_int,
    entry_text,
    load_pane_entries,
    load_tab_entries,
    tab_id,
    workspace_id,
    workspace_label,
)
from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TMUX_EXPORT_SHELL_COMMAND,
    TmuxExportCommandSource,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _tab_display_name(tab: JsonObject) -> str:
    number = entry_int(tab, "number")
    return (
        entry_text(tab, "label")
        or (f"tab-{number}" if number is not None else None)
        or tab_id(tab)
        or "tab"
    )


def _unique_tab_name(tab: JsonObject, used_tab_names: set[str]) -> str:
    tab_name = _tab_display_name(tab=tab).strip()
    if tab_name == "":
        tab_name = "tab"
    if tab_name not in used_tab_names:
        used_tab_names.add(tab_name)
        return tab_name

    tab_id_value = tab_id(tab)
    indexed_tab_name = f"{tab_name}-{tab_id_value}" if tab_id_value is not None else tab_name
    if indexed_tab_name not in used_tab_names:
        used_tab_names.add(indexed_tab_name)
        return indexed_tab_name

    suffix = 2
    while True:
        candidate_name = f"{indexed_tab_name}-{suffix}"
        if candidate_name not in used_tab_names:
            used_tab_names.add(candidate_name)
            return candidate_name
        suffix += 1


def _panes_by_tab_id(panes: Iterable[JsonObject]) -> dict[str, list[JsonObject]]:
    grouped_panes: dict[str, list[JsonObject]] = {}
    for pane in panes:
        tab_id_value = entry_text(pane, "tab_id")
        if tab_id_value is None:
            continue
        tab_panes = grouped_panes.get(tab_id_value)
        if tab_panes is None:
            grouped_panes[tab_id_value] = [pane]
        else:
            tab_panes.append(pane)
    return grouped_panes


def _select_representative_pane(
    tab: JsonObject,
    panes_by_tab: dict[str, list[JsonObject]],
) -> JsonObject | None:
    tab_id_value = tab_id(tab=tab)
    if tab_id_value is None:
        return None
    tab_panes = panes_by_tab.get(tab_id_value, [])
    for pane in tab_panes:
        if bool(pane.get("focused")):
            return pane
    if len(tab_panes) == 0:
        return None
    return tab_panes[0]


def _cwd_from_entry(entry: JsonObject | None) -> str | None:
    if entry is None:
        return None
    return (
        entry_text(entry, "foreground_cwd")
        or entry_text(entry, "cwd")
        or entry_text(entry, "start_dir")
        or entry_text(entry, "startDir")
    )


def _start_dir_from_tab(tab: JsonObject, pane: JsonObject | None) -> str:
    cwd = _cwd_from_entry(entry=pane) or _cwd_from_entry(entry=tab)
    if cwd is None:
        return str(Path.home())
    return cwd


def _workspace_label_counts(workspaces: list[JsonObject]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for workspace in workspaces:
        label = workspace_label(workspace=workspace)
        if label is not None:
            counts[label] = counts.get(label, 0) + 1
    return counts


def _layout_name_for_workspace(
    workspace: JsonObject,
    label_counts: dict[str, int],
) -> str:
    label = workspace_label(workspace=workspace)
    workspace_id_value = workspace_id(workspace=workspace)
    if label is not None and label_counts.get(label, 0) == 1:
        return label
    if workspace_id_value is not None:
        return workspace_id_value
    if label is not None:
        return label
    raise ValueError("Herdr workspace cannot be exported because it has no label or workspace_id.")


def _build_layout_for_herdr_workspace(
    workspace: JsonObject,
    label_counts: dict[str, int],
) -> LayoutConfig:
    workspace_id_value = workspace_id(workspace=workspace)
    layout_name = _layout_name_for_workspace(
        workspace=workspace,
        label_counts=label_counts,
    )
    if workspace_id_value is None:
        raise ValueError(f"Herdr workspace '{layout_name}' cannot be exported because workspace_id is missing.")
    tabs = load_tab_entries(workspace_id_value=workspace_id_value)
    if len(tabs) == 0:
        raise ValueError(f"Herdr workspace '{layout_name}' has no tabs to export.")
    panes = load_pane_entries(workspace_id_value=workspace_id_value)
    panes_by_tab = _panes_by_tab_id(panes=panes)

    used_tab_names: set[str] = set()
    layout_tabs: list[TabConfig] = []
    for tab in tabs:
        representative_pane = _select_representative_pane(
            tab=tab,
            panes_by_tab=panes_by_tab,
        )
        layout_tabs.append(
            {
                "tabName": _unique_tab_name(
                    tab=tab,
                    used_tab_names=used_tab_names,
                ),
                "startDir": _start_dir_from_tab(
                    tab=tab,
                    pane=representative_pane,
                ),
                "command": TMUX_EXPORT_SHELL_COMMAND,
            }
        )
    return {"layoutName": layout_name, "layoutTabs": layout_tabs}


def build_layouts_from_herdr_workspaces(
    workspaces: list[JsonObject],
    command_source: TmuxExportCommandSource,
) -> list[LayoutConfig]:
    if command_source != "shell":
        raise ValueError("Herdr export only supports --command-source shell.")
    if len(workspaces) == 0:
        raise ValueError("No Herdr workspaces were selected for export.")
    label_counts = _workspace_label_counts(workspaces=workspaces)
    return [
        _build_layout_for_herdr_workspace(
            workspace=workspace,
            label_counts=label_counts,
        )
        for workspace in workspaces
    ]
