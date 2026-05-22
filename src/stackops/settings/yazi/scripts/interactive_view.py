from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import Final, Literal, NoReturn, cast

type Command = list[str]
type ViewerMode = Literal["auto", "browser", "markdown", "database", "visidata"]

HOVERED_MARKER = "__YAZI_HOVERED__"
SELECTED_MARKER = "__YAZI_SELECTED__"
DUCKDB_SUFFIXES: Final[frozenset[str]] = frozenset({".duckdb", ".ddb"})
BROWSER_DOCUMENT_SUFFIXES: Final[frozenset[str]] = frozenset({".html", ".htm", ".pdf"})
BROWSER_IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".apng", ".avif", ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
)
BROWSER_FILE_SUFFIXES: Final[frozenset[str]] = BROWSER_DOCUMENT_SUFFIXES | BROWSER_IMAGE_SUFFIXES
MARKDOWN_SUFFIXES: Final[frozenset[str]] = frozenset({".md", ".markdown"})
SQLITE_SUFFIXES: Final[frozenset[str]] = frozenset({".db", ".db3", ".s3db", ".sl3", ".sqlite", ".sqlite3"})
VISIDATA_SUFFIXES: Final[frozenset[str]] = frozenset({".json", ".parquet", ".tsv", ".xlsx", ".csv"})


def build_browser_command(target_path: Path) -> Command:
    return [sys.executable, str(Path(__file__).with_name("serve_browser_file.py")), str(target_path)]


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
            raise ValueError("Interactive view requires exactly one selected path.")
        return Path(selected_paths[0]).resolve()
    if hovered_path is None:
        raise ValueError("No hovered path or selected path was provided.")
    return Path(hovered_path).resolve()


def build_database_command(target_path: Path, database_backend: str = "harlequin") -> Command:
    from stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend import BACKEND_LOOSE, build_read_db_cli_tui_command

    if target_path.suffix.lower() not in DUCKDB_SUFFIXES | SQLITE_SUFFIXES:
        raise ValueError(f"No database view command is configured for {target_path.suffix or 'files without an extension'}.")
    return build_read_db_cli_tui_command(
        path=str(target_path),
        backend=cast(BACKEND_LOOSE, database_backend),
        read_only=True,
    )


def build_markdown_command(target_path: Path) -> Command:
    return ["glow", "--tui", str(target_path)]


def build_visidata_command(target_path: Path) -> Command:
    return [(Path.home() / ".config/stackops/scripts/wrap_stackops").as_posix(), "croshell", "-b", "v", str(target_path)]


def build_command(target_path: Path, mode: ViewerMode = "auto", database_backend: str = "harlequin") -> Command:
    if target_path.is_dir():
        return build_browser_command(target_path=target_path)
    if not target_path.is_file():
        raise ValueError(f"Interactive view requires a file or directory, got: {target_path}")
    match mode:
        case "browser":
            return build_browser_command(target_path=target_path)
        case "markdown":
            return build_markdown_command(target_path=target_path)
        case "database":
            return build_database_command(target_path=target_path, database_backend=database_backend)
        case "visidata":
            return build_visidata_command(target_path=target_path)
        case "auto":
            pass
    suffix = target_path.suffix.lower()
    match suffix:
        case _ if suffix in BROWSER_FILE_SUFFIXES:
            return build_browser_command(target_path=target_path)
        case _ if suffix in MARKDOWN_SUFFIXES:
            return build_markdown_command(target_path=target_path)
        case _ if suffix in DUCKDB_SUFFIXES or suffix in SQLITE_SUFFIXES:
            return build_database_command(target_path=target_path, database_backend=database_backend)
        case suffix if suffix in VISIDATA_SUFFIXES:
            return build_visidata_command(target_path=target_path)
        case _:
            raise ValueError(f"No interactive view command is configured for {target_path.suffix or 'files without an extension'}.")


def exec_command(command: Command) -> NoReturn:
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
