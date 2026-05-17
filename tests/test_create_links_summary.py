from stackops.profile.create_links import (
    MAX_ERROR_TABLE_CHARS,
    _operation_record_has_error,
    _summary_table_value,
    _truncate_error_for_summary,
)
from stackops.utils.links import OperationRecord


def _record(*, action: str, details: str, status: str) -> OperationRecord:
    return {
        "program": "git",
        "file_key": "config",
        "defaultPath": "/home/alex/.gitconfig",
        "selfManaged": "/home/alex/dotfiles/.gitconfig",
        "operation": "down_symlink",
        "action": action,  # type: ignore[typeddict-item]
        "details": details,
        "status": status,
    }


def test_error_summary_values_are_truncated_to_first_30_chars() -> None:
    full_error = "error: this is a very long conflict message that would stretch the table"
    record = _record(action="error", details=full_error, status=full_error)

    assert _operation_record_has_error(record)
    assert _summary_table_value(record, "details") == f"{full_error[:MAX_ERROR_TABLE_CHARS]}..."
    assert _summary_table_value(record, "status") == f"{full_error[:MAX_ERROR_TABLE_CHARS]}..."


def test_success_summary_values_keep_full_text() -> None:
    details = "long but successful details should stay untouched in the summary"
    record = _record(action="linking", details=details, status="success")

    assert not _operation_record_has_error(record)
    assert _summary_table_value(record, "details") == details
    assert _summary_table_value(record, "status") == "success"


def test_error_summary_values_are_single_line() -> None:
    assert _truncate_error_for_summary("error line 1\nerror line 2") == "error line 1 error line 2"
