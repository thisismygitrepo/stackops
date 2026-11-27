from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig

OFF_MARK = " (off)"


# What a launch opens: no layout, tab or pane that is switched off, and no tab or layout that is left with nothing in it. Naming a layout
# or a tab switches it on for that launch before this is asked, so what is still off here was not asked for.
def drop_disabled(layouts: list[LayoutConfig]) -> list[LayoutConfig]:
    kept_layouts: list[LayoutConfig] = []
    for layout in layouts:
        if not layout.get("enabled", True):
            continue
        kept_tabs: list[TabConfig] = []
        for tab in layout["layoutTabs"]:
            panes = [pane for pane in tab["panes"] if pane.get("enabled", True)]
            if tab.get("enabled", True) and panes:
                kept_tabs.append({**tab, "panes": panes})
        if kept_tabs:
            kept_layouts.append({**layout, "layoutTabs": kept_tabs})
    if not kept_layouts:
        raise ValueError("Nothing to launch: everything selected is switched off (enabled: false). Name a layout or a tab to launch it anyway.")
    return kept_layouts


# A layout saved from a running session holds only what was running. The tabs and panes that were switched off in the layout it replaces
# were not, so they are put back where they were.
def keep_disabled_entries(existing_layout: LayoutConfig, new_layout: LayoutConfig) -> LayoutConfig:
    existing_tabs = {tab["tabName"]: tab for tab in reversed(existing_layout["layoutTabs"])}
    merged_tabs: list[TabConfig] = []
    for new_tab in new_layout["layoutTabs"]:
        existing_tab = existing_tabs.get(new_tab["tabName"])
        if existing_tab is None:
            merged_tabs.append(new_tab)
            continue
        new_pane_names = {pane["paneName"] for pane in new_tab["panes"]}
        panes = list(new_tab["panes"])
        for pane_index, pane in enumerate(existing_tab["panes"]):
            if not pane.get("enabled", True) and pane["paneName"] not in new_pane_names:
                panes.insert(pane_index, pane)
        merged_tabs.append({**new_tab, "panes": panes})
    new_tab_names = {tab["tabName"] for tab in new_layout["layoutTabs"]}
    for tab_index, tab in enumerate(existing_layout["layoutTabs"]):
        if not tab.get("enabled", True) and tab["tabName"] not in new_tab_names:
            merged_tabs.insert(tab_index, tab)
    return {**new_layout, "layoutTabs": merged_tabs}
