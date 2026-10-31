from collections.abc import Iterable

from stackops.scripts.python.helpers.helpers_sessions.herdr_export_source import (
    JsonObject,
    entry_int,
    entry_text,
    load_pane_entries,
    load_pane_origins,
    load_tab_entries,
    tab_id,
    workspace_id,
    workspace_label,
)
from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TMUX_EXPORT_SHELL_COMMAND,
)
from stackops.utils.schemas.layouts.layout_arrangement import infer_arrangement_from_origins
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabConfig


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


def _start_dir_from_pane(pane: JsonObject) -> str:
    cwd = entry_text(pane, "foreground_cwd") or entry_text(pane, "cwd")
    if cwd is None:
        raise ValueError(f"Herdr pane {entry_text(pane, 'pane_id')} does not report its working directory.")
    return cwd


def _export_tab_panes(
    tab_name: str,
    tab_panes: list[JsonObject],
) -> tuple[list[PaneConfig], list[tuple[int, int]]]:
    if len(tab_panes) == 0:
        raise ValueError(f"Herdr tab '{tab_name}' has no panes to export.")
    panes_by_id: dict[str, JsonObject] = {}
    for pane in tab_panes:
        pane_id = entry_text(pane, "pane_id")
        if pane_id is None:
            raise ValueError(f"Herdr tab '{tab_name}' contains a pane without a pane_id.")
        panes_by_id[pane_id] = pane
    origins_by_pane_id = load_pane_origins(pane_id_value=next(iter(panes_by_id)))
    pane_ids_row_major = sorted(
        panes_by_id,
        key=lambda pane_id: (origins_by_pane_id[pane_id][1], origins_by_pane_id[pane_id][0]),
    )
    used_pane_names: set[str] = set()
    panes: list[PaneConfig] = []
    for pane_index, pane_id in enumerate(pane_ids_row_major):
        pane = panes_by_id[pane_id]
        pane_name = entry_text(pane, "label") or f"pane-{pane_index + 1}"
        if pane_name in used_pane_names:
            pane_name = f"{pane_name}-{pane_index + 1}"
        used_pane_names.add(pane_name)
        panes.append(
            {
                "paneName": pane_name,
                "startDir": _start_dir_from_pane(pane=pane),
                "command": TMUX_EXPORT_SHELL_COMMAND,
            }
        )
    return panes, [origins_by_pane_id[pane_id] for pane_id in pane_ids_row_major]


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
        tab_name = _unique_tab_name(tab=tab, used_tab_names=used_tab_names)
        panes, origins = _export_tab_panes(
            tab_name=tab_name,
            tab_panes=panes_by_tab.get(tab_id(tab) or "", []),
        )
        layout_tab: TabConfig = {"tabName": tab_name, "panes": panes}
        if len(panes) > 1:
            layout_tab["arrangement"] = infer_arrangement_from_origins(origins=origins)
        layout_tabs.append(layout_tab)
    return {"layoutName": layout_name, "layoutTabs": layout_tabs}


def build_layouts_from_herdr_workspaces(
    workspaces: list[JsonObject],
) -> list[LayoutConfig]:
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
