from pathlib import Path

from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import resolve_doctor_definitions
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.rich_output import render_doctor_reports
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import build_doctor_report


def run_doctor(*, requested_agent: str, working_directory: Path) -> None:
    definitions = resolve_doctor_definitions(requested_agent=requested_agent)
    reports = tuple(build_doctor_report(definition=definition, working_directory=working_directory) for definition in definitions)
    render_doctor_reports(console=Console(), reports=reports)
