from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import Final, NoReturn

HOVERED_MARKER = "__YAZI_HOVERED__"
SELECTED_MARKER = "__YAZI_SELECTED__"
DUCKDB_SUFFIXES: Final[frozenset[str]] = frozenset({".duckdb", ".ddb"})
SQLITE_SUFFIXES: Final[frozenset[str]] = frozenset({".db", ".db3", ".s3db", ".sl3", ".sqlite", ".sqlite3"})
VISIDATA_SUFFIXES: Final[frozenset[str]] = frozenset({".json", ".parquet", ".tsv", ".xlsx", ".csv"})


def split_marked_arguments(arguments: Sequence[str]) -> tuple[str | None, list[str]]:
    tokens = list(arguments)
    try:
        hovered_marker_index = tokens.index(HOVERED_MARKER)
        selected_marker_index = tokens.index(SELECTED_MARKER)
    except ValueError as error:
        raise ValueError("Missing Yazi argument markers.") from error
    if hovered_marker_index >= selected_marker_index:
        raise ValueError("Yazi argument markers are out of order.")
    hovered_tokens = tokens[hovered_marker_index + 1 : selected_marker_index]
    if len(hovered_tokens) > 1:
        raise ValueError("Expected at most one hovered path.")
    hovered_path = hovered_tokens[0] if hovered_tokens else None
    selected_paths = tokens[selected_marker_index + 1 :]
    return hovered_path, selected_paths


def resolve_target(arguments: Sequence[str]) -> Path:
    hovered_path, selected_paths = split_marked_arguments(arguments)
    if selected_paths:
        if len(selected_paths) != 1:
            raise ValueError("Interactive view requires exactly one selected file.")
        return Path(selected_paths[0]).resolve()
    if hovered_path is None:
        raise ValueError("No hovered file or selected file was provided.")
    return Path(hovered_path).resolve()


def build_database_command(target_path: Path) -> list[str]:
    suffix = target_path.suffix.lower()
    path_string = str(target_path)
    if suffix in DUCKDB_SUFFIXES:
        return ["harlequin", "--adapter", "duckdb", "--read-only", path_string]
    if suffix in SQLITE_SUFFIXES:
        return ["harlequin", "--adapter", "sqlite", "--read-only", path_string]
    raise ValueError(f"No database view command is configured for {target_path.suffix or 'files without an extension'}.")


def build_command(target_path: Path) -> list[str]:
    if not target_path.is_file():
        raise ValueError(f"Interactive view requires a file, got: {target_path}")
    suffix = target_path.suffix.lower()
    match suffix:
        case _ if suffix in DUCKDB_SUFFIXES or suffix in SQLITE_SUFFIXES:
            return build_database_command(target_path=target_path)
        case suffix if suffix in VISIDATA_SUFFIXES:
            return [str(Path.home() / ".config/stackops/scripts/wrap_mcfg"), "croshell", "-b", "v", str(target_path)]
        case _:
            raise ValueError(f"No interactive view command is configured for {target_path.suffix or 'files without an extension'}.")


def exec_command(command: list[str]) -> NoReturn:
    executable = command[0]
    remaining_arguments = tuple(command[1:])
    os.execlp(executable, executable, *remaining_arguments)


def main(arguments: Sequence[str]) -> int:
    try:
        target_path = resolve_target(arguments)
        command = build_command(target_path=target_path)
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    try:
        exec_command(command)
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 127


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
