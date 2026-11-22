from dataclasses import dataclass

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppTab, BrowserAppWindow, BrowserWindowsUnavailable
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_TAB_PICKER_PREVIEW_SIZE_PERCENT, BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_status import BrowserLaunchWindowsStatus, OpenBrowserStatus


@dataclass(frozen=True)
class BrowserTabTarget:
    browser: BrowserName
    process_id: int
    port: int | None
    window: BrowserAppWindow
    tab: BrowserAppTab


def collect_open_browser_tabs(*, rows: tuple[OpenBrowserStatus, ...]) -> tuple[BrowserTabTarget, ...]:
    return tuple(
        BrowserTabTarget(browser=row.browser.browser, process_id=row.browser.process_id, port=row.browser.debugging_port, window=window, tab=tab)
        for row in rows
        if not isinstance(row.browser_windows, BrowserWindowsUnavailable)
        for window in row.browser_windows
        for tab in window.tabs
    )


def collect_launch_tabs(*, statuses: tuple[BrowserLaunchWindowsStatus, ...]) -> tuple[BrowserTabTarget, ...]:
    return tuple(
        BrowserTabTarget(browser=status.launch.browser, process_id=status.browser_process_id, port=status.launch.browser_port, window=window, tab=tab)
        for status in statuses
        if not isinstance(status.browser_windows, BrowserWindowsUnavailable) and status.browser_process_id is not None
        for window in status.browser_windows
        for tab in window.tabs
    )


def show_browser_tabs(*, tabs: tuple[BrowserTabTarget, ...], unreadable_browser_count: int) -> None:
    table = Table(
        title=f"Open tabs: {len(tabs)}",
        caption=None
        if unreadable_browser_count == 0
        else f"Not listed: tabs of {unreadable_browser_count} browser(s) that cannot be read (see the Windows column above)",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Browser")
    table.add_column("PID", justify="right")
    table.add_column("Window")
    table.add_column("Title")
    table.add_column("URL")
    for target in tabs:
        table.add_row(
            target.browser,
            str(target.process_id),
            target.window.window_id,
            Text(target.tab.title or "-", no_wrap=True, overflow="ellipsis"),
            Text(target.tab.url, no_wrap=True, overflow="ellipsis"),
        )
    Console().print(table)


def choose_browser_tab(*, tabs: tuple[BrowserTabTarget, ...]) -> BrowserTabTarget | None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    index_width = len(str(len(tabs)))
    targets_by_label = {
        f"""{index:>{index_width}}  {target.browser} {target.process_id}  {target.tab.title or "-"}  {target.tab.url}""": target
        for index, target in enumerate(tabs, start=1)
    }
    selected_label = choose_from_dict_with_preview(
        options_to_preview_mapping={
            label: f"""Title:   {target.tab.title or "-"}
URL:     {target.tab.url}
Browser: {target.browser} (PID {target.process_id}, {"no debug port" if target.port is None else f"debug port {target.port}"})
Window:  {target.window.window_id} · {target.window.state} · {len(target.window.tabs)} {"tab" if len(target.window.tabs) == 1 else "tabs"}"""
            for label, target in targets_by_label.items()
        },
        extension="txt",
        multi=False,
        preview_size_percent=BROWSER_TAB_PICKER_PREVIEW_SIZE_PERCENT,
    )
    return None if selected_label is None else targets_by_label[selected_label]
