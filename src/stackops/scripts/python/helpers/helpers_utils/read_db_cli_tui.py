
from pathlib import Path
import glob as glob_module
import os
import shutil
from typing import Literal, TypeAlias

BACKEND_LOOSE: TypeAlias = Literal[
    "rainfrog", "r",
    "lazysql", "l",
    "dblab", "d",
    "usql", "u",
    "harlequin", "h",
    "sqlit", "s"
]
BACKEND: TypeAlias = Literal[
    "rainfrog",
    "lazysql",
    "dblab",
    "usql",
    "harlequin",
    "sqlit"
]
LOOSE2STRICT: dict[BACKEND_LOOSE, BACKEND] = {
    "rainfrog": "rainfrog", "r": "rainfrog",
    "lazysql": "lazysql",   "l": "lazysql",
    "dblab": "dblab",       "d": "dblab",
    "usql": "usql",         "u": "usql",
    "harlequin": "harlequin", "h": "harlequin",
    "sqlit": "sqlit",       "s": "sqlit",
}

# harlequin is the only backend that can open multiple DB files simultaneously
MULTI_DB_CAPABLE: frozenset[BACKEND] = frozenset({"harlequin"})
# backends that can natively handle duckdb connection strings
DUCKDB_CAPABLE: frozenset[BACKEND] = frozenset({"harlequin", "rainfrog", "usql"})
READ_ONLY_CAPABLE: frozenset[BACKEND] = frozenset({"harlequin", "lazysql"})
SQLITE_URL_READ_ONLY_CAPABLE: frozenset[BACKEND] = frozenset({"rainfrog"})

DUCKDB_EXTS: frozenset[str] = frozenset({".duckdb", ".ddb"})
SQLITE_EXTS: frozenset[str] = frozenset({".sqlite", ".sqlite3", ".db", ".db3", ".s3db", ".sl3"})
EXT_TO_PREFIX: dict[str, str] = {
    ".duckdb": "duckdb://", ".ddb": "duckdb://",
    ".sqlite": "sqlite://", ".sqlite3": "sqlite://", ".db": "sqlite://",
    ".db3": "sqlite://", ".s3db": "sqlite://", ".sl3": "sqlite://",
    ".postgres": "postgres://", ".pg": "postgres://", ".postgresql": "postgres://",
    ".mysql": "mysql://",
}


def _find_files(pattern: str, root: Path, recursive: bool) -> list[Path]:
    glob_base = str(root / "**" / pattern) if recursive else str(root / pattern)
    return sorted(Path(p).resolve() for p in glob_module.glob(glob_base, recursive=recursive))


def _url_for(p: Path) -> str:
    prefix = EXT_TO_PREFIX.get(p.suffix.lower(), "sqlite://")
    return f"{prefix}{p}"


def _rainfrog_sqlite_read_only_url(path: Path) -> str:
    file_uri_path = path.resolve().as_uri().removeprefix("file://")
    return f"""sqlite://{file_uri_path}?mode=ro"""


def _rainfrog_command(path: Path | None, read_only: bool) -> list[str]:
    command = ["rainfrog"]
    if path is None:
        return command
    suffix = path.suffix.lower()
    if suffix in DUCKDB_EXTS:
        return [*command, "--driver", "duckdb", "--database", str(path)]
    if suffix in SQLITE_EXTS:
        if read_only:
            return [*command, "--url", _rainfrog_sqlite_read_only_url(path)]
        return [*command, "--driver", "sqlite", "--database", str(path)]
    return [*command, "--url", str(path)]


def _database_family(path: Path) -> Literal["duckdb", "sqlite", "other"]:
    suffix = path.suffix.lower()
    if suffix in DUCKDB_EXTS:
        return "duckdb"
    if suffix in SQLITE_EXTS:
        return "sqlite"
    return "other"


def _harlequin_adapter(resolved: list[Path]) -> Literal["duckdb", "sqlite"] | None:
    if not resolved:
        return None
    families = {_database_family(path) for path in resolved}
    if families == {"duckdb"}:
        return "duckdb"
    if families == {"sqlite"}:
        return "sqlite"
    raise ValueError(f"Harlequin requires all opened local database files to use the same engine, got: {sorted(families)}")


def _harlequin_command(resolved: list[Path], read_only: bool, theme: str | None, limit: int | None) -> list[str]:
    command = ["harlequin"]
    adapter = _harlequin_adapter(resolved)
    if adapter is not None:
        command.extend(["--adapter", adapter])
    if read_only and resolved:
        command.append("--read-only")
    if theme is not None:
        command.extend(["--theme", theme])
    if limit is not None:
        command.extend(["--limit", str(limit)])
    command.extend(str(path) for path in resolved)
    return command


def _launch_interactive_command(command: list[str]) -> None:
    executable = command[0]
    if shutil.which(executable) is None:
        raise FileNotFoundError(f"Command not found: {executable}")
    os.execvp(executable, command)


def _validate_backend(backend: BACKEND, resolved: list[Path]) -> None:
    is_all_duckdb = all(p.suffix.lower() in DUCKDB_EXTS for p in resolved)
    if is_all_duckdb and backend not in DUCKDB_CAPABLE:
        duckdb_capable_list = ", ".join(sorted(DUCKDB_CAPABLE))
        raise ValueError(
            f"Backend '{backend}' does not support DuckDB files.\n"
            f"DuckDB-capable backends: {duckdb_capable_list}\n"
            f"Files: {[str(p) for p in resolved]}"
        )
    if len(resolved) > 1 and backend not in MULTI_DB_CAPABLE:
        multi_capable_list = ", ".join(sorted(MULTI_DB_CAPABLE))
        raise ValueError(
            f"Backend '{backend}' cannot open multiple files simultaneously.\n"
            f"Multi-file-capable backends: {multi_capable_list}\n"
            f"Files ({len(resolved)}): {[str(p) for p in resolved]}"
        )


def _validate_read_only_support(backend: BACKEND, read_only: bool, resolved: list[Path]) -> None:
    if not read_only or not resolved:
        return
    if backend in READ_ONLY_CAPABLE:
        return
    if backend in SQLITE_URL_READ_ONLY_CAPABLE:
        families = {_database_family(path) for path in resolved}
        if families == {"sqlite"}:
            return
    read_only_capable_list = ", ".join(sorted(READ_ONLY_CAPABLE | SQLITE_URL_READ_ONLY_CAPABLE))
    raise ValueError(
        f"Backend '{backend}' does not provide a verified read-only mode for the requested local database files.\n"
        f"Read-only-capable backends: {read_only_capable_list}\n"
        f"Rainfrog read-only support is limited to local SQLite files opened via URL mode.\n"
        f"Files: {[str(path) for path in resolved]}"
    )


def app(
    path: str | None = None,
    find: str | None = None,
    find_root: str | None = None,
    recursive: bool = False,
    backend: BACKEND_LOOSE = "harlequin",
    read_only: bool = True,
    theme: str | None = None,
    limit: int | None = None,
) -> None:
    """🗃️ TUI DB Visualizer.

    path       – explicit file path (single DB).
    find       – glob pattern to discover DB files, e.g. '*.duckdb' or '**/*.duckdb'.
    find_root  – root directory for `find` (default: current working directory).
    recursive  – search subdirectories when using `find`.
    """
    backend_strict = LOOSE2STRICT[backend]

    resolved: list[Path] = []
    if path is not None and find is not None:
        raise ValueError("Provide either `path` or `find`, not both.")
    if path is not None:
        resolved = [Path(path).expanduser().resolve()]
    elif find is not None:
        root = Path(find_root).expanduser().resolve() if find_root is not None else Path.cwd()
        resolved = _find_files(find, root, recursive)
        if not resolved:
            raise FileNotFoundError(f"No files matched pattern '{find}' under '{root}' (recursive={recursive})")
        print(f"Found {len(resolved)} file(s) matching '{find}' under '{root}'")

    if resolved:
        _validate_backend(backend_strict, resolved)
        _validate_read_only_support(backend_strict, read_only, resolved)

    command: list[str]
    match backend_strict:
        case "rainfrog":
            command = _rainfrog_command(resolved[0] if resolved else None, read_only=read_only)
        case "lazysql":
            command = ["lazysql"]
            if read_only:
                command.append("-read-only")
            if resolved:
                command.append(_url_for(resolved[0]))
        case "dblab":
            command = ["dblab"]
            if limit is not None:
                command.extend(["--limit", str(limit)])
            if resolved:
                command.extend(["--url", _url_for(resolved[0])])
        case "usql":
            command = ["usql"]
            if resolved:
                command.append(_url_for(resolved[0]))
        case "harlequin":
            command = _harlequin_command(resolved=resolved, read_only=read_only, theme=theme, limit=limit)
        case "sqlit":
            command = ["sqlit"]
            if theme is not None:
                command.extend(["--theme", theme])
            if limit is not None:
                command.extend(["--max-rows", str(limit)])
            if resolved:
                command.append(_url_for(resolved[0]))

    _launch_interactive_command(command)
