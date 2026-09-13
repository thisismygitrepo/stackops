from typing import cast

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Select, TabbedContent, TabPane, TextArea

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive import CleanupSelection
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory, HookRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_AGENT_DEFINITIONS
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_cleanup import cleanup_action, cleanup_details, cleanup_kind


class CleanupResourceTable(DataTable[Text]):
    BINDINGS = [Binding("space", "select_cursor", "Toggle resource")]


class CleanupBrowser(Vertical):
    DEFAULT_CSS = """
    CleanupBrowser { height: 1fr; }
    CleanupBrowser .filters { height: 3; }
    CleanupBrowser Select { width: 1fr; }
    CleanupBrowser Input { width: 1fr; }
    CleanupBrowser #cleanup-panes { height: 1fr; }
    CleanupBrowser #cleanup-resources { width: 3fr; border: round $primary; }
    CleanupBrowser TabbedContent { width: 2fr; }
    CleanupBrowser TabPane { padding: 0; }
    CleanupBrowser TextArea { height: 1fr; }
    """

    class Changed(Message):
        pass

    def __init__(self, *, selection: CleanupSelection) -> None:
        super().__init__()
        self.cleanup_initial = selection
        self.cleanup_inventory = HookInventory(entries=(), diagnostics=())
        self.cleanup_selected: set[HookRemoval] = set()
        self.cleanup_visible: list[int] = []

    def compose(self) -> ComposeResult:
        kinds = ["all", "hook", "mcp", "plugin", "skill", "instructions", "configuration"]
        if self.cleanup_initial.resource not in kinds:
            kinds.append(self.cleanup_initial.resource)
        with Horizontal(classes="filters"):
            yield Select[str](
                [("All agents", "all"), *((item.display_name, item.agent) for item in DOCTOR_AGENT_DEFINITIONS)],
                value=self.cleanup_initial.agent, allow_blank=False, id="cleanup-agent",
            )
            yield Select[str]([("All types" if kind == "all" else kind, kind) for kind in kinds],
                              value=self.cleanup_initial.resource, allow_blank=False, id="cleanup-kind")
            yield Select[str]([(scope, scope) for scope in ("all", "local", "global", "admin", "system")],
                              value=self.cleanup_initial.scope, allow_blank=False, id="cleanup-scope")
        with Horizontal(classes="filters"):
            yield Input(value=self.cleanup_initial.match or "", placeholder="Filter names, commands, paths…", id="cleanup-search")
            yield Button("Select shown", id="cleanup-select")
            yield Button("Clear", id="cleanup-clear")
        with Horizontal(id="cleanup-panes"):
            yield CleanupResourceTable(id="cleanup-resources", cursor_type="row", zebra_stripes=True)
            with TabbedContent():
                with TabPane("Resource"):
                    yield TextArea("Select a row to inspect its source and reset action.", read_only=True, id="cleanup-detail")
                with TabPane("Diagnostics"):
                    yield TextArea(read_only=True, id="cleanup-diagnostics")

    def on_mount(self) -> None:
        table = self.query_one(CleanupResourceTable)
        for label, width in (("✓", 3), ("Resource", 30), ("Type", 14), ("Agent", 12), ("Scope", 8), ("State", 12), ("Action", 28)):
            table.add_column(label, key=label, width=width)
        table.border_title = "Resources · Space / Enter to select"

    def load_inventory(self, inventory: HookInventory) -> None:
        self.cleanup_inventory = inventory
        self.cleanup_selected.clear()
        notes = "\n\n".join(
            f"""{item.severity.upper()} · {item.agent} · {item.origin}
{item.path}
{item.message}""" for item in inventory.diagnostics
        )
        self.query_one("#cleanup-diagnostics", TextArea).load_text(notes or "No inspection diagnostics.")
        self.filter_resources()

    @on(Select.Changed)
    @on(Input.Changed, "#cleanup-search")
    def filter_resources(self) -> None:
        agent = self.query_one("#cleanup-agent", Select).value
        scope = self.query_one("#cleanup-scope", Select).value
        kinds = cast(str, self.query_one("#cleanup-kind", Select).value).split(",")
        search = self.query_one("#cleanup-search", Input).value.casefold()
        self.cleanup_visible = [
            index for index, entry in enumerate(self.cleanup_inventory.entries)
            if (agent == "all" or entry.agent == agent) and (scope == "all" or entry.origin == scope)
            and ("all" in kinds or cleanup_kind(entry) in kinds)
            and search in f"""{entry.name} {entry.event} {entry.command} {entry.path}""".casefold()
        ]
        table = self.query_one(CleanupResourceTable)
        table.clear()
        for index in self.cleanup_visible:
            entry = self.cleanup_inventory.entries[index]
            marker = "✓" if entry.removal in self.cleanup_selected else "·" if entry.removal is not None and entry.origin in ("local", "global") else "—"
            table.add_row(
                *(Text(value) for value in (marker, entry.name, cleanup_kind(entry), entry.agent, entry.origin, entry.state, cleanup_action(entry))),
                key=str(index),
            )
        detail = cleanup_details(entry=self.cleanup_inventory.entries[self.cleanup_visible[0]], entries=self.cleanup_inventory.entries) if self.cleanup_visible else "No matching resources. Adjust the filters."
        self.query_one("#cleanup-detail", TextArea).load_text(detail)
        table.border_subtitle = f"""{len(self.cleanup_visible)} shown / {len(self.cleanup_inventory.entries)} found"""
        self.post_message(self.Changed())

    @on(DataTable.RowHighlighted, "#cleanup-resources")
    def show_resource(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key.value is not None:
            index = int(event.row_key.value)
            if index in self.cleanup_visible:
                self.query_one("#cleanup-detail", TextArea).load_text(
                    cleanup_details(entry=self.cleanup_inventory.entries[index], entries=self.cleanup_inventory.entries),
                )

    @on(DataTable.RowSelected, "#cleanup-resources")
    def toggle_resource(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value is None:
            return
        entry = self.cleanup_inventory.entries[int(event.row_key.value)]
        if entry.removal is None or entry.origin not in ("local", "global"):
            self.notify("This resource is read only.", severity="warning")
            return
        if entry.removal in self.cleanup_selected:
            self.cleanup_selected.remove(entry.removal)
        else:
            self.cleanup_selected.add(entry.removal)
        self.update_marks()

    @on(Button.Pressed, "#cleanup-select")
    @on(Button.Pressed, "#cleanup-clear")
    def select_resources(self, event: Button.Pressed) -> None:
        if event.button.id == "cleanup-clear":
            self.cleanup_selected.clear()
        else:
            self.cleanup_selected.update(
                entry.removal for index in self.cleanup_visible
                if (entry := self.cleanup_inventory.entries[index]).removal is not None and entry.origin in ("local", "global")
            )
        self.update_marks()

    def update_marks(self) -> None:
        table = self.query_one(CleanupResourceTable)
        for index in self.cleanup_visible:
            entry = self.cleanup_inventory.entries[index]
            marker = "✓" if entry.removal in self.cleanup_selected else "·" if entry.removal is not None and entry.origin in ("local", "global") else "—"
            table.update_cell(str(index), "✓", Text(marker, style="bold green" if marker == "✓" else ""))
        self.post_message(self.Changed())
