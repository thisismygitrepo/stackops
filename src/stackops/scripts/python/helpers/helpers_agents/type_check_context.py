import json
from typing import cast

from stackops.scripts.python.ai.scripts.constants import REPORT_SCHEMA_VERSION
from stackops.scripts.python.ai.scripts.report_schema import ToolReport


class DiagnosticBatch(ToolReport):
    sourceDiagnosticCount: int


def read_type_check_report(payload: object) -> ToolReport:
    if not isinstance(payload, dict):
        raise ValueError("Expected a type-check JSON report object")
    report = cast(dict[str, object], payload)
    if report.get("schemaVersion") != REPORT_SCHEMA_VERSION:
        raise ValueError("Unsupported type-check report schemaVersion; rerun type-check")
    if report.get("status") not in ("ok", "empty"):
        raise ValueError(f"""Cannot fix diagnostics from report status {report.get('status')}: {report.get('error')}""")
    if not isinstance(report.get("tool"), str):
        raise ValueError("Type-check report is missing its tool name")
    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise ValueError("Type-check report diagnostics must be an array")
    if report.get("diagnosticCount") != len(diagnostics):
        raise ValueError("Type-check report diagnosticCount does not match its diagnostics")
    for diagnostic in cast(list[object], diagnostics):
        if not isinstance(diagnostic, dict):
            raise ValueError("Each diagnostic must contain diagnosticNumber and diagnosticValue")
        entry = cast(dict[str, object], diagnostic)
        number = entry.get("diagnosticNumber")
        if type(number) is not int or number < 1 or "diagnosticValue" not in entry:
            raise ValueError("Each diagnostic must contain a positive diagnosticNumber and diagnosticValue")
    if not diagnostics and report.get("exitCode") != 0:
        raise ValueError(f"""Checker exited with code {report.get('exitCode')} without usable diagnostics; rerun type-check""")
    return cast(ToolReport, payload)


def chunk_type_check_report(payload: object, agent_load: int) -> list[str]:
    if agent_load < 1:
        raise ValueError("--agent-load must be a positive integer")
    report = read_type_check_report(payload)
    diagnostics = report["diagnostics"]
    batches: list[str] = []
    for index in range(0, len(diagnostics), agent_load):
        entries = diagnostics[index : index + agent_load]
        batch: DiagnosticBatch = {
            **report,
            "diagnosticCount": len(entries),
            "sourceDiagnosticCount": len(diagnostics),
            "diagnostics": entries,
        }
        batches.append(json.dumps(batch, indent=2, ensure_ascii=False) + "\n")
    return batches
