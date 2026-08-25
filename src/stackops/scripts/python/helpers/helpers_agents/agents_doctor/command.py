from pathlib import Path
from typing import Final, cast, get_args

from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorResourceFocus
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


def run_doctor(*, requested_agent: str, working_directory: Path, requested_resources: str) -> None:
    definitions = resolve_doctor_definitions(requested_agent=requested_agent)
    resource_focuses = resolve_resource_focuses(requested_resources=requested_resources)
    reports = tuple(build_doctor_report(definition=definition, working_directory=working_directory) for definition in definitions)
    render_doctor_reports(console=Console(), reports=reports, resource_focuses=resource_focuses)
