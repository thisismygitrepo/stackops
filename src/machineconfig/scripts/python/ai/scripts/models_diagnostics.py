import json
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

try:
    from models_json import (  # type: ignore[import-not-found] # sibling script, resolved at runtime via sys.path
        extract_json_entries,
        parse_json_output,
    )
except ModuleNotFoundError:
    from machineconfig.scripts.python.ai.scripts.models_json import (
        extract_json_entries,
        parse_json_output,
    )


DIAGNOSTIC_DISTRIBUTION_LIMIT: Final[int] = 4
DiagnosticClassifier: TypeAlias = Literal[
    "check",
    "code",
    "name",
    "rule",
    "severity",
    "type",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class DiagnosticBucket:
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class DiagnosticSummary:
    total_count: int
    classifier: DiagnosticClassifier
    buckets: tuple[DiagnosticBucket, ...]


def build_diagnostic_summary(tool_slug: str, raw_output: str) -> DiagnosticSummary:
    if raw_output.strip() == "":
        return DiagnosticSummary(total_count=0, classifier="unknown", buckets=())
    try:
        parsed_output = parse_json_output(raw_output=raw_output)
    except json.JSONDecodeError:
        return DiagnosticSummary(total_count=0, classifier="unknown", buckets=())
    payload = parsed_output.payload
    if tool_slug == "pyright":
        return _build_pyright_summary(payload=payload)
    if tool_slug == "mypy":
        return _count_entries_by_fields(
            payload=payload,
            classifier="code",
            primary_field="code",
            fallback_field="severity",
            fallback_label="unknown",
        )
    if tool_slug == "pylint":
        return _build_pylint_summary(payload=payload)
    if tool_slug == "pyrefly":
        return _count_entries_by_fields(
            payload=payload,
            classifier="name",
            primary_field="name",
            fallback_field="severity",
            fallback_label="unknown",
        )
    if tool_slug == "ty":
        return _count_entries_by_fields(
            payload=payload,
            classifier="check",
            primary_field="check_name",
            fallback_field="severity",
            fallback_label="unknown",
        )
    if tool_slug == "ruff":
        return _count_entries_by_fields(
            payload=payload,
            classifier="rule",
            primary_field="code",
            fallback_field="severity",
            fallback_label="unknown",
        )
    return _count_entries_by_fields(
        payload=payload,
        classifier="unknown",
        primary_field="severity",
        fallback_field="code",
        fallback_label="unknown",
    )


def format_diagnostic_distribution(summary: DiagnosticSummary) -> str:
    if summary.total_count == 0:
        return "none"
    displayed_buckets = summary.buckets[:DIAGNOSTIC_DISTRIBUTION_LIMIT]
    fragments = [
        f"{bucket.label} {bucket.count}" for bucket in displayed_buckets
    ]
    remaining_bucket_count = len(summary.buckets) - len(displayed_buckets)
    if remaining_bucket_count > 0:
        fragments.append(f"+{remaining_bucket_count} more")
    return ", ".join(fragments)


def _build_pyright_summary(payload: object) -> DiagnosticSummary:
    if isinstance(payload, dict):
        summary_payload = payload.get("summary")
        if isinstance(summary_payload, dict):
            counts: dict[str, int] = {}
            known_keys = (
                ("errorCount", "error"),
                ("warningCount", "warning"),
                ("informationCount", "information"),
            )
            saw_known_key = False
            for source_key, bucket_label in known_keys:
                bucket_value = summary_payload.get(source_key)
                if isinstance(bucket_value, int):
                    saw_known_key = True
                    if bucket_value > 0:
                        counts[bucket_label] = bucket_value
            if saw_known_key:
                return _summary_from_counts(classifier="severity", counts=counts)
    return _count_entries_by_fields(
        payload=payload,
        classifier="severity",
        primary_field="severity",
        fallback_field="code",
        fallback_label="unknown",
    )


def _build_pylint_summary(payload: object) -> DiagnosticSummary:
    if isinstance(payload, dict):
        statistics_payload = payload.get("statistics")
        if isinstance(statistics_payload, dict):
            message_type_count = statistics_payload.get("messageTypeCount")
            if isinstance(message_type_count, dict):
                counts: dict[str, int] = {}
                saw_known_key = False
                for bucket_label in (
                    "fatal",
                    "error",
                    "warning",
                    "refactor",
                    "convention",
                    "info",
                ):
                    bucket_value = message_type_count.get(bucket_label)
                    if isinstance(bucket_value, int):
                        saw_known_key = True
                        if bucket_value > 0:
                            counts[bucket_label] = bucket_value
                if saw_known_key:
                    return _summary_from_counts(classifier="type", counts=counts)
    return _count_entries_by_fields(
        payload=payload,
        classifier="type",
        primary_field="type",
        fallback_field="symbol",
        fallback_label="unknown",
    )


def _count_entries_by_fields(
    payload: object,
    classifier: DiagnosticClassifier,
    primary_field: str,
    fallback_field: str,
    fallback_label: str,
) -> DiagnosticSummary:
    _, entries = extract_json_entries(payload=payload)
    if entries is None:
        return DiagnosticSummary(total_count=0, classifier=classifier, buckets=())
    counts: dict[str, int] = {}
    for entry in entries:
        bucket_label = _read_string_field(entry=entry, field_name=primary_field)
        if bucket_label is None:
            bucket_label = _read_string_field(entry=entry, field_name=fallback_field)
        if bucket_label is None:
            bucket_label = fallback_label
        _increment_count(counts=counts, bucket_label=bucket_label)
    return _summary_from_counts(classifier=classifier, counts=counts)


def _read_string_field(entry: object, field_name: str) -> str | None:
    if not isinstance(entry, dict):
        return None
    field_value = entry.get(field_name)
    if isinstance(field_value, str) and field_value != "":
        return field_value
    return None


def _increment_count(counts: dict[str, int], bucket_label: str) -> None:
    existing_count = counts.get(bucket_label)
    if existing_count is None:
        counts[bucket_label] = 1
        return
    counts[bucket_label] = existing_count + 1


def _summary_from_counts(
    classifier: DiagnosticClassifier, counts: dict[str, int]
) -> DiagnosticSummary:
    buckets = tuple(
        DiagnosticBucket(label=bucket_label, count=bucket_count)
        for bucket_label, bucket_count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
    )
    return DiagnosticSummary(
        total_count=sum(counts.values()),
        classifier=classifier,
        buckets=buckets,
    )
