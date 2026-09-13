from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Footer, Header, Input, Static
from textual.worker import get_current_worker

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.command import resolve_resource_focuses
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorReport
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import (
    DOCTOR_AGENT_DEFINITIONS,
    resolve_doctor_definitions,
)
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import build_doctor_report
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor_widgets import DoctorBrowser


class DoctorApp(App[None]):
    TITLE = "Agent Doctor"
    CSS = """
    #doctor-status { height: auto; padding: 0 1; }
    """
    BINDINGS = [
        Binding("f5", "inspect", "Refresh"),
        Binding("ctrl+f", "search", "Search", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, *, requested_agent: str, directory: str, requested_resources: str) -> None:
        super().__init__()
        requested_definitions = resolve_doctor_definitions(requested_agent=requested_agent)
        self.doctor_definitions = (*requested_definitions, *(
            definition for definition in DOCTOR_AGENT_DEFINITIONS if definition not in requested_definitions
        ))
        self.doctor_initial_agent = "all" if len(requested_definitions) > 1 else requested_definitions[0].agent
        self.doctor_focuses = resolve_resource_focuses(requested_resources=requested_resources)
        self.doctor_directory = Path(directory).expanduser().absolute()
        self.doctor_inspecting = False
        self.complete = False
        self.sub_title = str(self.doctor_directory)

    def compose(self) -> ComposeResult:
        yield Header()
        yield DoctorBrowser(initial_agent=self.doctor_initial_agent, resource_focuses=self.doctor_focuses)
        yield Static("Preparing inspection…", id="doctor-status", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self.action_inspect)
        self.query_one("#doctor-agents").focus()

    def action_search(self) -> None:
        search = self.query_one("#doctor-search", Input)
        search.focus()
        search.action_select_all()

    @on(Button.Pressed, "#doctor-refresh")
    def action_inspect(self) -> None:
        if self.doctor_inspecting:
            return
        self.doctor_inspecting = True
        self.complete = False
        self.query_one("#doctor-refresh", Button).disabled = True
        self.query_one("#doctor-status", Static).update("Inspecting… You can browse cached results while scans run.")
        self._inspect()

    @work(thread=True)
    def _inspect(self) -> None:
        worker = get_current_worker()
        reports: list[DoctorReport] = []
        try:
            for index, definition in enumerate(self.doctor_definitions, start=1):
                if worker.is_cancelled:
                    return
                self.call_from_thread(
                    lambda: self.query_one("#doctor-status", Static).update(
                        f"""Inspecting {definition.display_name} ({index}/{len(self.doctor_definitions)})… Browse and filter as results arrive."""
                    ),
                )
                report = build_doctor_report(definition=definition, working_directory=self.doctor_directory)
                reports.append(report)
                self.call_from_thread(lambda: self.query_one(DoctorBrowser).accept_report(report))
            complete = not any(report.inspection_errors for report in reports)
            status = (
                f"""{len(reports)} agents inspected · Select an agent or resource for details · F5 refreshes the scan"""
                if complete else "Inspection incomplete · Select agents marked Incomplete to read errors · F5 refreshes the scan"
            )
        except Exception as error:
            complete = False
            status = f"""Inspection failed: {error} · F5 to retry"""
        if not worker.is_cancelled:
            self.call_from_thread(self._finish_inspection, complete=complete, status=status)

    def _finish_inspection(self, *, complete: bool, status: str) -> None:
        self.complete = complete
        self.doctor_inspecting = False
        self.query_one("#doctor-refresh", Button).disabled = False
        self.query_one("#doctor-status", Static).update(status)


def run_doctor_tui(*, requested_agent: str, directory: str, requested_resources: str) -> None:
    app = DoctorApp(requested_agent=requested_agent, directory=directory, requested_resources=requested_resources)
    app.run()
    if not app.complete:
        raise SystemExit(1)
