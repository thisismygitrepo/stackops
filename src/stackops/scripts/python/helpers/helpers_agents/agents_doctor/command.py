from pathlib import Path
from typing import Final, cast, get_args

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorReport, DoctorResourceFocus
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import resolve_doctor_definitions
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.rich_output import render_doctor_reports
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import build_doctor_report


_DOCTOR_RESOURCE_FOCUSES: Final[tuple[DoctorResourceFocus, ...]] = cast(
    tuple[DoctorResourceFocus, ...], get_args(DoctorResourceFocus)
)


def resolve_resource_focuses(*, requested_resources: str) -> tuple[DoctorResourceFocus, ...]:
    raw_focuses = tuple(resource.strip().casefold() for resource in requested_resources.split(","))
    if any(resource == "" for resource in raw_focuses):
        raise ValueError("Resource focuses must be a comma-separated list without empty entries")
    unsupported_focuses = tuple(resource for resource in raw_focuses if resource not in _DOCTOR_RESOURCE_FOCUSES)
    if len(unsupported_focuses) > 0:
        supported_focuses = ", ".join(_DOCTOR_RESOURCE_FOCUSES)
        raise ValueError(f"Unsupported resource focus: {unsupported_focuses[0]}. Supported focuses: {supported_focuses}")
    resource_focuses = cast(tuple[DoctorResourceFocus, ...], tuple(dict.fromkeys(raw_focuses)))
    if "all" in resource_focuses and len(resource_focuses) > 1:
        raise ValueError("Do not mix 'all' with specific resource focuses")
    return resource_focuses


def run_doctor(*, requested_agent: str, working_directory: Path, requested_resources: str) -> bool:
    definitions = resolve_doctor_definitions(requested_agent=requested_agent)
    resource_focuses = resolve_resource_focuses(requested_resources=requested_resources)
    console = Console()
    reports: list[DoctorReport] = []
    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), TextColumn("agents"), TimeElapsedColumn(),
        console=console, disable=not console.is_terminal,
    ) as progress:
        task_id = progress.add_task("Inspecting agents", total=len(definitions))
        for index, definition in enumerate(definitions, start=1):
            description = f"""Inspecting {definition.display_name}"""
            progress.update(task_id, description=description, refresh=True)
            if not console.is_terminal:
                console.print(f"""[{index}/{len(definitions)}] {description}""", markup=False)
            reports.append(build_doctor_report(definition=definition, working_directory=working_directory))
            progress.advance(task_id)
        progress.update(task_id, description="Inspection finished", refresh=True)
    render_doctor_reports(console=console, reports=reports, resource_focuses=resource_focuses)
    return not any(report.inspection_errors for report in reports)
