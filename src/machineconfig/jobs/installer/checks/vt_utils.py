"""
VirusTotal Utilities
====================

This module provides functionality to interact with VirusTotal API.
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from rich.progress import Progress, TaskID

if TYPE_CHECKING:
    import vt


class ScanResult(TypedDict):
    category: str
    result: str | None


class ScanSummary(TypedDict):
    positive_pct: float
    total_engines: int
    verdict_engines: int
    flagged_engines: int
    malicious_engines: int
    suspicious_engines: int
    harmless_engines: int
    undetected_engines: int
    unsupported_engines: int
    timeout_engines: int
    failure_engines: int
    other_engines: int
    notes: str


VERDICT_CATEGORIES: tuple[str, ...] = ("malicious", "suspicious", "harmless", "undetected")


def get_vt_client() -> "vt.Client":
    VT_TOKEN_PATH = Path.home().joinpath("dotfiles/creds/tokens/virustotal")
    if not VT_TOKEN_PATH.exists():
        raise FileNotFoundError(f"VirusTotal token not found at {VT_TOKEN_PATH}")

    token = VT_TOKEN_PATH.read_text(encoding="utf-8").split("\n")[0].strip()
    import vt

    return vt.Client(token)


def _build_empty_scan_summary(notes: str) -> ScanSummary:
    return {
        "positive_pct": 0.0,
        "total_engines": 0,
        "verdict_engines": 0,
        "flagged_engines": 0,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 0,
        "undetected_engines": 0,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": notes,
    }


def _normalize_scan_result(result_item: object) -> ScanResult:
    category_raw = getattr(result_item, "category", "unknown")
    result_raw = getattr(result_item, "result", None)
    category = str(category_raw or "unknown")
    result = None if result_raw is None else str(result_raw)
    return {"category": category, "result": result}


def _build_scan_notes(summary: ScanSummary) -> str:
    if summary["total_engines"] == 0:
        return "VirusTotal returned no engine results."

    note_parts: list[str] = []
    if summary["timeout_engines"] > 0:
        note_parts.append(f"{summary['timeout_engines']} timed out")
    if summary["unsupported_engines"] > 0:
        note_parts.append(f"{summary['unsupported_engines']} unsupported")
    if summary["failure_engines"] > 0:
        note_parts.append(f"{summary['failure_engines']} failed")
    if summary["other_engines"] > 0:
        note_parts.append(f"{summary['other_engines']} uncategorized")
    if not note_parts:
        return "All reporting engines returned a verdict."
    return "Excluded from percentage: " + ", ".join(note_parts)


def summarize_scan_results(results_data: list[ScanResult]) -> ScanSummary:
    summary = _build_empty_scan_summary(notes="")
    summary["total_engines"] = len(results_data)

    for result_item in results_data:
        match result_item["category"]:
            case "malicious":
                summary["malicious_engines"] += 1
            case "suspicious":
                summary["suspicious_engines"] += 1
            case "harmless":
                summary["harmless_engines"] += 1
            case "undetected":
                summary["undetected_engines"] += 1
            case "type-unsupported":
                summary["unsupported_engines"] += 1
            case "timeout" | "confirmed-timeout":
                summary["timeout_engines"] += 1
            case "failure":
                summary["failure_engines"] += 1
            case _:
                summary["other_engines"] += 1

    summary["flagged_engines"] = summary["malicious_engines"] + summary["suspicious_engines"]
    summary["verdict_engines"] = sum(summary[key] for key in ("flagged_engines", "harmless_engines", "undetected_engines"))
    if summary["verdict_engines"] > 0:
        summary["positive_pct"] = round(summary["flagged_engines"] / summary["verdict_engines"] * 100, 1)
    summary["notes"] = _build_scan_notes(summary)
    return summary


def scan_file(
    path: Path,
    client: "vt.Client",
    progress: Progress | None = None,
    task_id: TaskID | None = None,
) -> tuple[ScanSummary | None, list[ScanResult]]:
    if path.is_dir():
        if progress is not None and task_id is not None:
            progress.console.print(f"[yellow]📁 Skipping directory: {path}[/yellow]")
        return None, []

    try:
        with path.open("rb") as file_handle:
            analysis = client.scan_file(file_handle)

        repeat_counter = 0
        while True:
            try:
                anal = client.get_object("/analyses/{}", analysis.id)
                if anal.status == "completed":
                    break
            except Exception as exc:
                repeat_counter += 1
                if repeat_counter > 3:
                    raise ValueError(f"❌ Error scanning {path}: {exc}") from exc
                if progress is not None and task_id is not None:
                    progress.console.print(f"[red]⚠️  Error scanning {path}, retrying... ({repeat_counter}/3)[/red]")
                time.sleep(5)

            time.sleep(10)

        raw_results = list(anal.results.values())
        results_data = [_normalize_scan_result(result_item) for result_item in raw_results]
        return summarize_scan_results(results_data), results_data
    except Exception as exc:
        if progress is not None and task_id is not None:
            progress.console.print(f"[bold red]❌ Failed to scan {path}: {exc}[/bold red]")
        return None, []
