from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Select, Static, TextArea

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorReport, DoctorResource, DoctorResourceFocus
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_AGENT_DEFINITIONS
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor_data import (
    doctor_health,
    doctor_health_details,
    doctor_resource_details,
)


class DoctorBrowser(Widget):
    DEFAULT_CSS = """
    DoctorBrowser { height: 1fr; }
    #doctor-filters { height: auto; padding: 0 1; }
    #doctor-filters Select { width: 1fr; }
    #doctor-search-row { height: auto; padding: 0 1; }
    #doctor-search { width: 1fr; }
    #doctor-refresh { margin-left: 1; }
    #doctor-body { height: 1fr; padding: 0 1; }
    #doctor-agent-pane { width: 2fr; min-width: 30; margin-right: 1; }
    #doctor-resource-pane { width: 5fr; }
    #doctor-agents, #doctor-health, #doctor-detail { height: 1fr; border: round $primary; }
    #doctor-resources { height: 2fr; border: round $primary; }
    #doctor-count { height: auto; color: $text-muted; }
    """

    def __init__(self, *, initial_agent: str, resource_focuses: tuple[DoctorResourceFocus, ...]) -> None:
        super().__init__()
        self.doctor_selected_agent = initial_agent
        self.doctor_focuses = resource_focuses
        self.doctor_reports: dict[str, DoctorReport] = {}
        self.doctor_rows: dict[str, tuple[DoctorReport, DoctorResource]] = {}
        self.doctor_selected_row = ""
        self.doctor_ready = False

    def compose(self) -> ComposeResult:
        kinds = [("All kinds", "all")]
        if len(self.doctor_focuses) > 1:
            kinds.append((f"""Requested: {', '.join(self.doctor_focuses)}""", "requested"))
        kinds.extend((kind.title(), kind) for kind in ("configuration", "mcp", "hook", "plugin", "skill", "instructions"))
        with Horizontal(id="doctor-filters"):
            yield Select[str](kinds, value=self.doctor_focuses[0] if len(self.doctor_focuses) == 1 else "requested", allow_blank=False, id="doctor-kind")
            yield Select[str]([("All scopes", "all"), *((scope.title(), scope) for scope in ("local", "global", "admin", "system"))], value="all", allow_blank=False, id="doctor-scope")
            yield Select[str]([("All states", "all"), *((state.title(), state) for state in ("active", "available", "configured", "referenced", "disabled", "missing", "shadowed"))], value="all", allow_blank=False, id="doctor-state")
        with Horizontal(id="doctor-search-row"):
            yield Input(placeholder="Search resource names, paths and details…", id="doctor-search")
            yield Button("Refresh", variant="primary", id="doctor-refresh")
        with Horizontal(id="doctor-body"):
            with Vertical(id="doctor-agent-pane"):
                yield DataTable(cursor_type="row", id="doctor-agents")
                yield TextArea("Select an agent for health and coverage details.", read_only=True, show_line_numbers=False, soft_wrap=True, id="doctor-health")
            with Vertical(id="doctor-resource-pane"):
                yield Static("Waiting for inspection…", id="doctor-count", markup=False)
                yield DataTable(cursor_type="row", id="doctor-resources")
                yield TextArea("Select a resource to inspect its provenance and path.", read_only=True, show_line_numbers=False, soft_wrap=True, id="doctor-detail")

    def on_mount(self) -> None:
        agents = self.query_one("#doctor-agents", DataTable)
        agents.border_title = "Agent health"
        for name, width in (("Agent", 18), ("Health", 13), ("#", 4)):
            agents.add_column(name, key=name, width=width)
        agents.add_row("All agents", "Pending", "0", key="all")
        for definition in DOCTOR_AGENT_DEFINITIONS:
            agents.add_row(definition.display_name, "Pending", "—", key=definition.agent)
        agent_names = ["all", *(definition.agent for definition in DOCTOR_AGENT_DEFINITIONS)]
        agents.move_cursor(row=agent_names.index(self.doctor_selected_agent))
        resources = self.query_one("#doctor-resources", DataTable)
        resources.border_title = "Resources"
        for name, width in (("Name", 28), ("Kind", 13), ("Scope", 7), ("State", 10), ("Agent", 18)):
            resources.add_column(name, width=width)
        self.query_one("#doctor-health", TextArea).border_title = "Health and coverage"
        self.query_one("#doctor-detail", TextArea).border_title = "Resource details · Select text to copy"
        self.doctor_ready = True
        self._show_health()

    def accept_report(self, report: DoctorReport) -> None:
        self.doctor_reports[report.definition.agent] = report
        table = self.query_one("#doctor-agents", DataTable)
        table.update_cell(report.definition.agent, "Health", doctor_health(report=report))
        table.update_cell(report.definition.agent, "#", str(len(report.resources)))
        table.update_cell("all", "Health", f"""{len(self.doctor_reports)}/{len(DOCTOR_AGENT_DEFINITIONS)} scanned""")
        table.update_cell("all", "#", str(sum(len(item.resources) for item in self.doctor_reports.values())))
        if self.doctor_selected_agent in ("all", report.definition.agent):
            self._show_health()
            self._filter_resources()

    @on(DataTable.RowHighlighted, "#doctor-agents")
    def select_agent(self, event: DataTable.RowHighlighted) -> None:
        if not self.doctor_ready or event.row_key.value is None:
            return
        self.doctor_selected_agent = event.row_key.value
        self._show_health()
        self._filter_resources()

    @on(DataTable.RowHighlighted, "#doctor-resources")
    def select_resource(self, event: DataTable.RowHighlighted) -> None:
        row = self.doctor_rows.get(str(event.row_key.value))
        if row is not None:
            self.doctor_selected_row = str(event.row_key.value)
            self.query_one("#doctor-detail", TextArea).load_text(doctor_resource_details(report=row[0], resource=row[1]))

    @on(Select.Changed)
    @on(Input.Changed, "#doctor-search")
    def change_filter(self) -> None:
        if self.doctor_ready:
            self._filter_resources()

    def _show_health(self) -> None:
        report = self.doctor_reports.get(self.doctor_selected_agent)
        if report is not None:
            content = doctor_health_details(report=report)
        elif self.doctor_selected_agent == "all":
            reports = tuple(self.doctor_reports.values())
            lines = [
                f"""{len(reports)} of {len(DOCTOR_AGENT_DEFINITIONS)} agents inspected""",
                f"""{sum(report.executable.installed for report in reports)} binaries installed""",
                f"""{sum(bool(report.inspection_errors) for report in reports)} incomplete inspections""",
                "",
                "Select an agent to see its executable, version, coverage and inspection notes.",
            ]
            for item in reports:
                if item.inspection_errors:
                    lines.extend(("", item.definition.display_name, *item.inspection_errors))
            content = "\n".join(lines)
        else:
            content = "Waiting for this agent's scan. Results appear as inspection progresses."
        self.query_one("#doctor-health", TextArea).load_text(content)

    def _filter_resources(self) -> None:
        kind = self.query_one("#doctor-kind", Select).value
        focuses = self.doctor_focuses if kind == "requested" else (kind,)
        scope = self.query_one("#doctor-scope", Select).value
        state = self.query_one("#doctor-state", Select).value
        search = self.query_one("#doctor-search", Input).value.casefold()
        rows: dict[str, tuple[DoctorReport, DoctorResource]] = {}
        total = 0
        for report in self.doctor_reports.values():
            if self.doctor_selected_agent not in ("all", report.definition.agent):
                continue
            total += len(report.resources)
            for index, resource in enumerate(report.resources):
                if not any(focus == "all" or focus == resource.kind or focus == "mcp" and resource.is_mcp for focus in focuses):
                    continue
                if scope not in ("all", resource.origin) or state not in ("all", resource.state):
                    continue
                searchable = f"""{resource.name} {resource.path} {resource.detail} {report.definition.display_name}""".casefold()
                if search in searchable:
                    rows[f"""{report.definition.agent}:{index}"""] = (report, resource)
        self.doctor_rows = rows
        table = self.query_one("#doctor-resources", DataTable)
        table.clear()
        for key, (report, resource) in rows.items():
            table.add_row(*(Text(value) for value in (
                resource.name, "MCP" if resource.is_mcp else resource.kind,
                resource.origin, resource.state, report.definition.display_name,
            )), key=key)
        keys = tuple(rows)
        selected = keys.index(self.doctor_selected_row) if self.doctor_selected_row in rows else 0
        detail = self.query_one("#doctor-detail", TextArea)
        if keys:
            self.doctor_selected_row = keys[selected]
            table.move_cursor(row=selected)
            report, resource = rows[keys[selected]]
            detail.load_text(doctor_resource_details(report=report, resource=resource))
        else:
            self.doctor_selected_row = ""
            detail.load_text("No resources match the current filters. Agent health and coverage remain available on the left.")
        self.query_one("#doctor-count", Static).update(f"""{len(rows)} of {total} resources · Arrow keys to browse · Ctrl+F to search""")
