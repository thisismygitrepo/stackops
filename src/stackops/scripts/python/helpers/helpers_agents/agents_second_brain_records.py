import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_constants import (
    AGENT_BY_LABEL,
    FOLLOWUP_AGENT,
    UPDATE_COLUMNS,
)


@dataclass(frozen=True, slots=True)
class UpdateRecord:
    agent: FOLLOWUP_AGENT
    session_id: str
    topic: str
    updated_on: date


@dataclass(frozen=True, slots=True)
class InvalidUpdateRow:
    line_number: int
    reason: str


@dataclass(frozen=True, slots=True)
class UpdateFile:
    path: Path
    records: list[UpdateRecord]
    invalid_rows: list[InvalidUpdateRow]
    error: str | None
    cleaned_text: str


def _parse_update_row(*, fields: list[str], line_number: int) -> UpdateRecord | InvalidUpdateRow:
    if len(fields) != len(UPDATE_COLUMNS):
        return InvalidUpdateRow(
            line_number=line_number,
            reason=f"""Expected {len(UPDATE_COLUMNS)} columns, found {len(fields)}.""",
        )
    empty_columns = [column for column, value in zip(UPDATE_COLUMNS, fields, strict=True) if value.strip() == ""]
    if empty_columns:
        return InvalidUpdateRow(line_number=line_number, reason=f"""Empty values: {', '.join(empty_columns)}.""")

    agent_label, session_id, topic, _actions_taken, updated_on_text = fields
    agent = AGENT_BY_LABEL.get(agent_label.strip().casefold())
    if agent is None:
        return InvalidUpdateRow(line_number=line_number, reason=f"""Unsupported agent '{agent_label}'.""")
    try:
        updated_on = datetime.fromisoformat(updated_on_text.strip()).date()
    except ValueError:
        return InvalidUpdateRow(
            line_number=line_number,
            reason=f"""Invalid date '{updated_on_text}'. Expected an ISO date or datetime.""",
        )
    return UpdateRecord(agent=agent, session_id=session_id.strip(), topic=topic.strip(), updated_on=updated_on)


def read_second_brain_updates(*, second_brain_root: Path) -> list[UpdateFile]:
    if not second_brain_root.is_dir():
        raise ValueError(f"""Second Brain directory is not available: {second_brain_root}""")

    update_files: list[UpdateFile] = []
    for update_path in sorted(path for path in second_brain_root.rglob("update.csv") if path.is_file()):
        with update_path.open(mode="r", encoding="utf-8", newline="") as update_file:
            lines = update_file.readlines()
        reader = csv.reader(lines, strict=True)
        records: list[UpdateRecord] = []
        invalid_rows: list[InvalidUpdateRow] = []
        retained_lines: list[str] = []
        file_error: str | None = None
        try:
            header = next(reader, None)
            if header != list(UPDATE_COLUMNS):
                expected = ",".join(UPDATE_COLUMNS)
                actual = ",".join(header or [])
                file_error = f"""Invalid header. Expected '{expected}', found '{actual}'."""
            else:
                previous_line = reader.line_num
                retained_lines.extend(lines[:previous_line])
                for fields in reader:
                    row_start = previous_line
                    previous_line = reader.line_num
                    parsed_row = _parse_update_row(fields=fields, line_number=row_start + 1)
                    match parsed_row:
                        case UpdateRecord():
                            records.append(parsed_row)
                            retained_lines.extend(lines[row_start:reader.line_num])
                        case InvalidUpdateRow():
                            invalid_rows.append(parsed_row)
        except csv.Error as parse_error:
            file_error = f"""Malformed CSV at line {reader.line_num}: {parse_error}."""
        update_files.append(
            UpdateFile(
                path=update_path,
                records=records if file_error is None else [],
                invalid_rows=invalid_rows if file_error is None else [],
                error=file_error,
                cleaned_text="".join(retained_lines) if file_error is None else "".join(lines),
            )
        )
    return update_files


def align_second_brain_updates(*, update_files: list[UpdateFile], force: bool) -> dict[Path, int]:
    file_errors = [f"""{update_file.path}: {update_file.error}""" for update_file in update_files if update_file.error is not None]
    if file_errors:
        details = "\n".join(file_errors)
        raise ValueError(f"""Cannot remove invalid updates until these CSV files are corrected. No files changed.
{details}""")

    removed_by_path: dict[Path, int] = {}
    for update_file in update_files:
        if update_file.invalid_rows:
            if force:
                update_file.path.write_text(update_file.cleaned_text, encoding="utf-8", newline="")
            removed_by_path[update_file.path] = len(update_file.invalid_rows)
    return removed_by_path
