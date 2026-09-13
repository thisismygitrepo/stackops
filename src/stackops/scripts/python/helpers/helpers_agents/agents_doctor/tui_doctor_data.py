from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorReport, DoctorResource


def doctor_health(*, report: DoctorReport) -> Text:
    if report.inspection_errors:
        return Text("Incomplete", style="bold red")
    if not report.executable.installed:
        return Text("Missing", style="red")
    if report.executable.error:
        return Text("Version error", style="yellow")
    return Text("Installed", style="green")


def doctor_health_details(*, report: DoctorReport) -> str:
    lines = [
        f"""{report.definition.display_name} ({report.definition.agent})""",
        f"""Binary: {'Installed' if report.executable.installed else 'Missing'}""",
        f"""Executable: {report.executable.path or report.definition.executable}""",
        f"""Version: {report.executable.version or 'Unavailable'}""",
        f"""Coverage: {report.definition.support_level}""",
        f"""Inspection: {'Incomplete' if report.inspection_errors else 'Complete'}""",
        f"""Resources: {len(report.resources)}""",
        f"""Working directory: {report.context.working_directory}""",
        f"""Project root: {report.context.project_root}""",
    ]
    if report.executable.error:
        lines.extend(("", "Version error", report.executable.error))
    if report.inspection_errors:
        lines.extend(("", "Inspection errors", *report.inspection_errors))
    notes = (*report.definition.notes, *report.inspection_notes)
    if notes:
        lines.extend(("", "Coverage and inspection notes", *notes))
    return "\n".join(lines)


def doctor_resource_details(*, report: DoctorReport, resource: DoctorResource) -> str:
    provenance = {
        "local": "Local project",
        "global": "Inherited from user configuration",
        "admin": "Inherited from administrator configuration",
        "system": "Bundled with the system",
    }[resource.origin]
    lines = [
        resource.name,
        f"""Agent: {report.definition.display_name}""",
        f"""Kind: {resource.kind}{' · MCP' if resource.is_mcp else ''}""",
        f"""State: {resource.state}""",
        f"""Provenance: {provenance}""",
        "",
        "Path",
        str(resource.path),
        "",
        "Why this resource is included",
        resource.detail,
        "",
        doctor_health_details(report=report),
    ]
    return "\n".join(lines)
