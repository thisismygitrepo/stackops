from collections.abc import Mapping
from typing import TYPE_CHECKING, TypedDict, cast

from stackops.jobs.installer.checks.constants import VT_REQUEST_TIMEOUT_SECONDS

if TYPE_CHECKING:
    import vt


class ScanResult(TypedDict):
    engine_name: str
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


def get_vt_client(api_key: str) -> "vt.Client":
    import vt

    return vt.Client(api_key, timeout=VT_REQUEST_TIMEOUT_SECONDS)


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


def normalize_scan_results(raw_results: object) -> list[ScanResult]:
    if not isinstance(raw_results, Mapping):
        raise ValueError("VirusTotal engine results must be a mapping.")
    results_data: list[ScanResult] = []
    for engine_name, result_item in cast(Mapping[object, object], raw_results).items():
        if not isinstance(engine_name, str) or not engine_name or not isinstance(result_item, Mapping):
            raise ValueError("VirusTotal engine entries must have names and mapped results.")
        engine_result = cast(Mapping[object, object], result_item)
        category = engine_result.get("category")
        result = engine_result.get("result")
        if not isinstance(category, str) or not category or (result is not None and not isinstance(result, str)):
            raise ValueError("VirusTotal engine category and result fields are malformed.")
        results_data.append({"engine_name": engine_name, "category": category, "result": result})
    return results_data


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
