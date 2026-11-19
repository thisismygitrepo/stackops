from typing import TypedDict

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_configuration import configuration_cleanup
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorOrigin, DoctorReport


class DoctorMcpServer(TypedDict):
    name: str
    origin: DoctorOrigin
    path: str
    detail: str


def declared_mcp_servers(*, report: DoctorReport) -> list[DoctorMcpServer]:
    present_configurations = {
        resource.path: resource for resource in report.resources if resource.kind == "configuration" and resource.state != "missing"
    }
    return [
        {"name": entry.name, "origin": entry.origin, "path": str(entry.path), "detail": entry.command}
        for resource in present_configurations.values()
        for entry in configuration_cleanup(
            agent=report.definition.agent, resource=resource, focuses=("mcp",), context=report.context
        ).entries
        if entry.event == "mcp"
    ]
