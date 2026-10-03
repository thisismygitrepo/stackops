import socket
from datetime import datetime

from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, OptionList, Static
from textual.widgets.option_list import Option
from textual.worker import get_current_worker

from stackops.scripts.python.helpers.helpers_devops.devops_status_constants import (
    COMPACT_WIDTH,
    STATUS_STYLES,
    STATUS_TITLES,
    StatusSection,
)
from stackops.scripts.python.helpers.helpers_devops.devops_status_data import StatusSnapshot, collect_status_section


class StatusApp(App[None]):
    TITLE = "StackOps · Machine status"
    CSS = """
    Screen { background: $surface; }
    Header { background: $primary-background; }
    #toolbar { height: 3; padding: 0 1; align-vertical: middle; }
    #summary { width: 1fr; height: auto; }
    #refresh { min-width: 12; margin-left: 1; }
    #workspace { height: 1fr; padding: 0 1; }
    #sections { width: 31; height: 1fr; border: round $primary; margin-right: 1; }
    #sections > .option-list--option { padding: 0 1; }
    #detail-pane { width: 1fr; }
    #section-summary { height: auto; padding: 0 1 1 1; }
    #details { height: 1fr; border: round $primary; padding: 1; }
    #content { height: auto; }
    #hint { height: auto; color: $text-muted; padding: 0 1; }
    .compact #workspace { layout: vertical; }
    .compact #sections { width: 1fr; height: 7; margin: 0 0 1 0; }
    .compact #detail-pane { width: 1fr; height: 1fr; }
    .compact #details { padding: 0; }
    """
    BINDINGS = [
        Binding("r,f5", "reload", "Refresh"),
        Binding("q,ctrl+q,escape", "quit", "Quit", priority=True),
        Binding("right,l", "focus_details", "Details", show=False),
        Binding("left,h", "focus_sections", "Sections", show=False),
        *(Binding(str(index + 1), f"""select_section({index})""", "Section", show=False) for index in range(7)),
    ]

    def __init__(self, *, sections: tuple[StatusSection, ...]) -> None:
        super().__init__()
        self.sections = sections
        self.selected_section: StatusSection = sections[0]
        self.snapshots: dict[StatusSection, StatusSnapshot] = {}
        self.refreshing = False
        self.checked = 0
        self.sub_title = socket.gethostname()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="toolbar"):
            yield Static("Preparing status checks…", id="summary", markup=False)
            yield Button("Refresh", id="refresh", variant="primary")
        with Horizontal(id="workspace"):
            yield OptionList(*(
                Option(Text(f"""{index}. {STATUS_TITLES[section]}\n   Waiting…"""), id=section)
                for index, section in enumerate(self.sections, start=1)
            ), id="sections")
            with Vertical(id="detail-pane"):
                yield Static("Waiting for this check…", id="section-summary", markup=False)
                with VerticalScroll(id="details"):
                    yield Static("Results appear as checks finish.", id="content", markup=False)
        yield Static("↑↓ sections · 1–7 jump · Tab / ←→ focus · PgUp/PgDn scroll", id="hint", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.screen.set_class(self.size.width < COMPACT_WIDTH, "compact")
        self.query_one("#sections", OptionList).border_title = "Sections"
        self.query_one("#sections", OptionList).focus()
        self.show_section()
        self.call_after_refresh(self.action_reload)

    def on_resize(self, event: events.Resize) -> None:
        self.screen.set_class(event.size.width < COMPACT_WIDTH, "compact")

    @on(OptionList.OptionHighlighted, "#sections")
    def select_section(self, event: OptionList.OptionHighlighted) -> None:
        self.selected_section = self.sections[event.option_index]
        self.query_one("#details", VerticalScroll).scroll_home(animate=False)
        self.show_section()

    def action_select_section(self, index: int) -> None:
        if index < len(self.sections):
            self.query_one("#sections", OptionList).highlighted = index
            self.query_one("#sections", OptionList).focus()

    def action_focus_details(self) -> None:
        details = self.query_one("#details", VerticalScroll)
        details.focus()

    def action_focus_sections(self) -> None:
        sections = self.query_one("#sections", OptionList)
        sections.focus()

    def show_section(self) -> None:
        self.query_one("#details", VerticalScroll).border_title = STATUS_TITLES[self.selected_section]
        snapshot = self.snapshots.get(self.selected_section)
        if snapshot is None:
            self.query_one("#section-summary", Static).update("Waiting for this check…")
            self.query_one("#content", Static).update("Results appear as checks finish. You can browse other sections now.")
        else:
            self.query_one("#section-summary", Static).update(Text(snapshot.summary, style=STATUS_STYLES[snapshot.level]))
            self.query_one("#content", Static).update(snapshot.content)

    @on(Button.Pressed, "#refresh")
    def action_reload(self) -> None:
        if self.refreshing:
            return
        self.refreshing = True
        self.checked = 0
        self.query_one("#refresh", Button).disabled = True
        sections = self.query_one("#sections", OptionList)
        for index, section in enumerate(self.sections, start=1):
            sections.replace_option_prompt(section, Text(f"""{index}. {STATUS_TITLES[section]}\n   Waiting…""", style="dim"))
        self.scan_sections()

    @work(thread=True)
    def scan_sections(self) -> None:
        worker = get_current_worker()
        for section in self.sections:
            if worker.is_cancelled:
                return
            self.call_from_thread(self.show_progress, section)
            snapshot = collect_status_section(section)
            if worker.is_cancelled:
                return
            self.call_from_thread(self.accept_snapshot, section, snapshot)
        self.call_from_thread(self.finish_refresh)

    def show_progress(self, section: StatusSection) -> None:
        self.query_one("#summary", Static).update(f"""Checking {STATUS_TITLES[section]}… {self.checked}/{len(self.sections)} complete""")
        index = self.sections.index(section) + 1
        self.query_one("#sections", OptionList).replace_option_prompt(
            section, Text(f"""{index}. {STATUS_TITLES[section]}\n   Checking…""", style="cyan"),
        )

    def accept_snapshot(self, section: StatusSection, snapshot: StatusSnapshot) -> None:
        self.snapshots[section] = snapshot
        self.checked += 1
        index = self.sections.index(section) + 1
        prompt = Text(f"""{index}. {STATUS_TITLES[section]}\n""", style="bold", no_wrap=True, overflow="ellipsis")
        prompt.append(f"""   {snapshot.summary}""", style=STATUS_STYLES[snapshot.level])
        self.query_one("#sections", OptionList).replace_option_prompt(section, prompt)
        if section == self.selected_section:
            self.show_section()

    def finish_refresh(self) -> None:
        self.refreshing = False
        self.query_one("#refresh", Button).disabled = False
        attention = sum(snapshot.level == "attention" for snapshot in self.snapshots.values())
        errors = sum(snapshot.level == "error" for snapshot in self.snapshots.values())
        updated = datetime.now().astimezone().strftime("%H:%M:%S")
        self.query_one("#summary", Static).update(
            f"""{self.checked} sections · {attention} need attention · {errors} errors · Updated {updated}"""
        )
