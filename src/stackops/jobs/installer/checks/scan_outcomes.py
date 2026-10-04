from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from stackops.jobs.installer.checks.vt_utils import ScanResult, ScanSummary

type ScanSource = Literal["existing_report", "submitted_file"]
type ScanStage = Literal["file read", "report lookup", "file upload", "analysis polling", "result parsing"]


@dataclass(frozen=True)
class ScanSuccess:
    summary: ScanSummary
    results: list[ScanResult]
    scanned_at: datetime
    source: ScanSource


@dataclass(frozen=True)
class ScanFailure:
    stage: ScanStage
    error_type: str
    error_code: str | None


@dataclass(frozen=True)
class ScanCancelled:
    pass


type ScanOutcome = ScanSuccess | ScanFailure | ScanCancelled


def format_scan_failure(failure: ScanFailure) -> str:
    error_type = failure.error_type if failure.error_type.isascii() and failure.error_type.isidentifier() else "UnknownError"
    error_code = failure.error_code
    if error_code is not None:
        error_code = error_code if error_code.isascii() and error_code.isidentifier() else "InvalidErrorCode"
    code_suffix = f" ({error_code})" if error_code is not None else ""
    return f"VirusTotal {failure.stage} failed: {error_type}{code_suffix}."
