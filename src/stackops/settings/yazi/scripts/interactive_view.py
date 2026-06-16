from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import Final, Literal, NoReturn

type Command = list[str]
type ViewerMode = Literal["auto", "browser", "markdown", "database", "visidata"]
type DatabaseBackend = Literal[
    "rainfrog",
    "lazysql",
    "dblab",
    "usql",
    "harlequin",
    "sqlit",
]

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
DUCKDB_CAPABLE: Final[frozenset[DatabaseBackend]] = frozenset({"harlequin", "rainfrog", "usql"})
READ_ONLY_CAPABLE: Final[frozenset[DatabaseBackend]] = frozenset({"harlequin", "lazysql"})
SQLITE_URL_READ_ONLY_CAPABLE: Final[frozenset[DatabaseBackend]] = frozenset({"rainfrog"})
LOOSE_TO_STRICT: Final[dict[str, DatabaseBackend]] = {
    "rainfrog": "rainfrog",
    "r": "rainfrog",
    "lazysql": "lazysql",
    "l": "lazysql",
    "dblab": "dblab",
    "d": "dblab",
    "usql": "usql",
    "u": "usql",
    "harlequin": "harlequin",
    "h": "harlequin",
    "sqlit": "sqlit",
    "s": "sqlit",
}
EXT_TO_PREFIX: Final[dict[str, str]] = {
    ".duckdb": "duckdb://",
    ".ddb": "duckdb://",
    ".sqlite": "sqlite://",
    ".sqlite3": "sqlite://",
    ".db": "sqlite://",
    ".db3": "sqlite://",
    ".s3db": "sqlite://",
    ".sl3": "sqlite://",
}


def build_browser_command(target_path: Path) -> Command:
    return [sys.executable, str(Path(__file__).with_name("serve_browser_file.py")), str(target_path)]


def normalize_database_backend(database_backend: str) -> DatabaseBackend:
    backend = LOOSE_TO_STRICT.get(database_backend)
    if backend is None:
        valid_backends = ", ".join(sorted(LOOSE_TO_STRICT))
        raise ValueError(f"Unknown database backend '{database_backend}'. Valid backends: {valid_backends}")
    return backend


def build_database_url(target_path: Path) -> str:
    prefix = EXT_TO_PREFIX[target_path.suffix.lower()]
    return f"{prefix}{target_path}"


def build_rainfrog_sqlite_read_only_url(target_path: Path) -> str:
    file_uri_path = target_path.resolve().as_uri().removeprefix("file://")
    return f"""sqlite://{file_uri_path}?mode=ro"""


def database_family(target_path: Path) -> Literal["duckdb", "sqlite"]:
    suffix = target_path.suffix.lower()
    if suffix in DUCKDB_SUFFIXES:
        return "duckdb"
    if suffix in SQLITE_SUFFIXES:
        return "sqlite"
    raise ValueError(f"No database view command is configured for {target_path.suffix or 'files without an extension'}.")


def validate_database_backend(target_path: Path, backend: DatabaseBackend, read_only: bool) -> None:
    family = database_family(target_path=target_path)
    if family == "duckdb" and backend not in DUCKDB_CAPABLE:
        duckdb_capable_list = ", ".join(sorted(DUCKDB_CAPABLE))
        raise ValueError(
            f"Backend '{backend}' does not support DuckDB files.\n"
            f"DuckDB-capable backends: {duckdb_capable_list}\n"
            f"File: {target_path}"
        )
    if not read_only:
        return
    if backend in READ_ONLY_CAPABLE:
        return
    if backend in SQLITE_URL_READ_ONLY_CAPABLE and family == "sqlite":
        return
    read_only_capable_list = ", ".join(sorted(READ_ONLY_CAPABLE | SQLITE_URL_READ_ONLY_CAPABLE))
    raise ValueError(
        f"Backend '{backend}' does not provide a verified read-only mode for the requested local database file.\n"
        f"Read-only-capable backends: {read_only_capable_list}\n"
        f"Rainfrog read-only support is limited to local SQLite files opened via URL mode.\n"
        f"File: {target_path}"
    )


def build_rainfrog_command(target_path: Path, read_only: bool) -> Command:
    suffix = target_path.suffix.lower()
    if suffix in DUCKDB_SUFFIXES:
        return ["rainfrog", "--driver", "duckdb", "--database", str(target_path)]
    if suffix in SQLITE_SUFFIXES:
        if read_only:
            return ["rainfrog", "--url", build_rainfrog_sqlite_read_only_url(target_path=target_path)]
        return ["rainfrog", "--driver", "sqlite", "--database", str(target_path)]
    return ["rainfrog", "--url", str(target_path)]


def build_harlequin_command(target_path: Path, read_only: bool) -> Command:
    command = ["harlequin", "--adapter", database_family(target_path=target_path)]
    if read_only:
        command.append("--read-only")
    command.append(str(target_path))
    return command


def build_database_backend_command(target_path: Path, backend: DatabaseBackend, read_only: bool) -> Command:
    match backend:
        case "rainfrog":
            return build_rainfrog_command(target_path=target_path, read_only=read_only)
        case "lazysql":
            command = ["lazysql"]
            if read_only:
                command.append("-read-only")
            command.append(build_database_url(target_path=target_path))
            return command
        case "dblab":
            return ["dblab", "--url", build_database_url(target_path=target_path)]
        case "usql":
            return ["usql", build_database_url(target_path=target_path)]
        case "harlequin":
            return build_harlequin_command(target_path=target_path, read_only=read_only)
        case "sqlit":
            return ["sqlit", build_database_url(target_path=target_path)]


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
    if target_path.suffix.lower() not in DUCKDB_SUFFIXES | SQLITE_SUFFIXES:
        raise ValueError(f"No database view command is configured for {target_path.suffix or 'files without an extension'}.")
    backend = normalize_database_backend(database_backend=database_backend)
    validate_database_backend(target_path=target_path, backend=backend, read_only=True)
    return build_database_backend_command(target_path=target_path, backend=backend, read_only=True)


def build_markdown_command(target_path: Path) -> Command:
    return ["glow", "--tui", str(target_path)]


def build_visidata_command(target_path: Path) -> Command:
    return [(Path.home() / ".config/stackops/scripts/wrap_stackops").as_posix(), "preview", "-b", "v", str(target_path)]


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
