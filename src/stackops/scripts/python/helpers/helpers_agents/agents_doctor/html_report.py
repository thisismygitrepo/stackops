import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.context_estimate import CONTEXT_ESTIMATE_CAPTION, estimate_context_definitions
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import (
    DoctorOrigin,
    DoctorReport,
    DoctorResourceFocus,
    DoctorResourceKind,
    DoctorResourceState,
    DoctorSupportLevel,
)
from stackops.utils.html_report import show_html_report


class DoctorHtmlResource(TypedDict):
    kind: DoctorResourceKind
    is_mcp: bool
    name: str
    origin: DoctorOrigin
    state: DoctorResourceState
    path: str
    detail: str


class DoctorHtmlContextEstimate(TypedDict):
    source: str
    files: int
    words: int
    tokens: int


class DoctorHtmlAgent(TypedDict):
    agent: str
    display_name: str
    executable: str
    installed: bool
    path: str | None
    version: str | None
    version_error: str | None
    support_level: DoctorSupportLevel
    resources: list[DoctorHtmlResource]
    context: list[DoctorHtmlContextEstimate]
    notes: list[str]
    errors: list[str]


class DoctorHtmlPayload(TypedDict):
    generated_at: str
    working_directory: str
    project_root: str
    home_directory: str
    focuses: list[DoctorResourceFocus]
    context_caption: str
    agents: list[DoctorHtmlAgent]


def show_doctor_html_report(*, reports: Sequence[DoctorReport], resource_focuses: tuple[DoctorResourceFocus, ...]) -> Path:
    all_focuses = resource_focuses == ("all",)
    context = reports[0].context
    payload: DoctorHtmlPayload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "working_directory": str(context.working_directory),
        "project_root": str(context.project_root),
        "home_directory": str(context.home_directory),
        "focuses": ["configuration", "mcp", "hook", "plugin", "skill", "instructions"] if all_focuses else list(resource_focuses),
        "context_caption": CONTEXT_ESTIMATE_CAPTION,
        "agents": [
            {
                "agent": report.definition.agent,
                "display_name": report.definition.display_name,
                "executable": report.definition.executable,
                "installed": report.executable.installed,
                "path": str(report.executable.path) if report.executable.path is not None else None,
                "version": report.executable.version,
                "version_error": report.executable.error,
                "support_level": report.definition.support_level,
                "resources": [
                    {
                        "kind": resource.kind,
                        "is_mcp": resource.is_mcp,
                        "name": resource.name,
                        "origin": resource.origin,
                        "state": resource.state,
                        "path": str(resource.path),
                        "detail": resource.detail,
                    }
                    for resource in report.resources
                    if all_focuses or resource.kind in resource_focuses or resource.is_mcp and "mcp" in resource_focuses
                ],
                "context": [
                    {
                        "source": estimate.source,
                        "files": estimate.file_count,
                        "words": estimate.word_count,
                        "tokens": estimate.estimated_tokens,
                    }
                    for estimate in estimate_context_definitions(report=report)
                ],
                "notes": [*report.definition.notes, *report.inspection_notes],
                "errors": list(report.inspection_errors),
            }
            for report in reports
        ],
    }
    asset_directory = Path(__file__).with_name("html_assets")
    return show_html_report(
        title="Agents doctor",
        payload_json=json.dumps(payload, ensure_ascii=False),
        style_path=asset_directory / "doctor.css",
        script_paths=(asset_directory / "doctor_data.js", asset_directory / "doctor_table.js", asset_directory / "doctor_views.js", asset_directory / "doctor_app.js"),
        file_stem="agents_doctor",
    )
