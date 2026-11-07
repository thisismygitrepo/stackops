from typing import Literal, TypedDict

from stackops.scripts.python.ai.scripts.models_core import ToolOutputFormat


type ToolReportStatus = Literal[
    "ok", "empty", "parse_failed", "unrecognized", "text", "start_failed"
]


class DiagnosticEntry(TypedDict):
    diagnosticNumber: int
    diagnosticValue: object


class ToolReport(TypedDict):
    schemaVersion: int
    tool: str
    title: str
    command: list[str]
    exitCode: int | None
    capturedFormat: ToolOutputFormat
    status: ToolReportStatus
    diagnosticCount: int | None
    prefixText: str
    stderr: str
    toolMetadata: dict[str, object]
    diagnostics: list[DiagnosticEntry]
    rawOutput: str | None
    payload: object
    error: str | None
