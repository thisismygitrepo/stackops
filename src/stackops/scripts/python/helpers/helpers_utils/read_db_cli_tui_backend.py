from pathlib import Path
from typing import Literal, TypeAlias

import typer

BACKEND_LOOSE: TypeAlias = Literal[
    "rainfrog", "r",
    "lazysql", "l",
    "dblab", "d",
    "usql", "u",
    "harlequin", "h",
    "sqlit", "s",
]
BACKEND: TypeAlias = Literal[
    "rainfrog",
    "lazysql",
    "dblab",
    "usql",
    "harlequin",
    "sqlit",
]
BACKEND_CHOICES: tuple[BACKEND, ...] = (
    "rainfrog",
    "lazysql",
    "dblab",
    "usql",
    "harlequin",
    "sqlit",
)

LOOSE_TO_STRICT: dict[BACKEND_LOOSE, BACKEND] = {
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

MULTI_DB_CAPABLE: frozenset[BACKEND] = frozenset({"harlequin"})
DUCKDB_CAPABLE: frozenset[BACKEND] = frozenset({"harlequin", "rainfrog", "usql"})
READ_ONLY_CAPABLE: frozenset[BACKEND] = frozenset({"harlequin", "lazysql"})
SQLITE_URL_READ_ONLY_CAPABLE: frozenset[BACKEND] = frozenset({"rainfrog"})

DUCKDB_EXTS: frozenset[str] = frozenset({".duckdb", ".ddb"})
SQLITE_EXTS: frozenset[str] = frozenset({".sqlite", ".sqlite3", ".db", ".db3", ".s3db", ".sl3"})
EXT_TO_PREFIX: dict[str, str] = {
    ".duckdb": "duckdb://",
    ".ddb": "duckdb://",
    ".sqlite": "sqlite://",
    ".sqlite3": "sqlite://",
    ".db": "sqlite://",
    ".db3": "sqlite://",
    ".s3db": "sqlite://",
    ".sl3": "sqlite://",
    ".postgres": "postgres://",
    ".pg": "postgres://",
    ".postgresql": "postgres://",
    ".mysql": "mysql://",
}
HARLEQUIN_URL_ADAPTERS: dict[str, str] = {
    "duckdb": "duckdb",
    "mysql": "mysql",
    "postgres": "postgres",
    "postgresql": "postgres",
    "sqlite": "sqlite",
}


def _find_files(pattern: str, root: Path, recursive: bool) -> list[Path]:
    import glob as glob_module
    glob_base = str(root / "**" / pattern) if recursive else str(root / pattern)
    return sorted(Path(p).resolve() for p in glob_module.glob(glob_base, recursive=recursive))


def _url_for(path: Path) -> str:
    prefix = EXT_TO_PREFIX.get(path.suffix.lower(), "sqlite://")
    return f"{prefix}{path}"


def _rainfrog_sqlite_read_only_url(path: Path) -> str:
    file_uri_path = path.resolve().as_uri().removeprefix("file://")
    return f"""sqlite://{file_uri_path}?mode=ro"""


def _looks_like_url(value: str) -> bool:
    from urllib.parse import urlsplit
    parsed = urlsplit(value)
    return bool(parsed.scheme) and "://" in value


def _format_command(command: list[str]) -> str:
    import os

    if os.name == "nt":
        import subprocess
        return subprocess.list2cmdline(command)
    import shlex
    return shlex.join(command)


def _print_built_command(command: list[str]) -> None:
    import sys
    print(f"Built command: {_format_command(command)}", file=sys.stderr, flush=True)


def _strip_ansi(value: str) -> str:
    import re
    return re.sub(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", value)


def _harlequin_installed_adapters() -> frozenset[str] | None:
    import re
    import shutil
    import subprocess
    from functools import cache

    @cache
    def _cached() -> frozenset[str] | None:
        if shutil.which("harlequin") is None:
            return None
        result = subprocess.run(["harlequin", "--help"], capture_output=True, check=False, text=True)
        if result.returncode != 0:
            return None
        normalized_stdout = _strip_ansi(result.stdout)
        match = re.search(r"--adapter.*?\n[^\n]*\(([^)]+)\)", normalized_stdout, re.DOTALL)
        if match is None:
            return None
        return frozenset(choice.strip() for choice in match.group(1).split("|") if choice.strip() != "")

    return _cached()


def _harlequin_url_adapter(url: str) -> str | None:
    from urllib.parse import urlsplit
    return HARLEQUIN_URL_ADAPTERS.get(urlsplit(url).scheme.lower())


def _validate_harlequin_url_adapter(url: str) -> None:
    requested_adapter = _harlequin_url_adapter(url)
    if requested_adapter is None:
        return
    installed_adapters = _harlequin_installed_adapters()
    if installed_adapters is None or requested_adapter in installed_adapters:
        return
    installed_adapter_list = ", ".join(sorted(installed_adapters))
    raise typer.BadParameter(
        message=(
            f"Installed harlequin does not support the '{requested_adapter}' adapter required for '{url}'.\n"
            f"Installed adapters: {installed_adapter_list}"
        ),
        param_hint="--url",
    )


def _rainfrog_command(path: Path | None, url: str | None, read_only: bool) -> list[str]:
    command = ["rainfrog"]
    if url is not None:
        return [*command, "--url", url]
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


def _harlequin_command(resolved: list[Path], url: str | None, read_only: bool, theme: str | None, limit: int | None) -> list[str]:
    command = ["harlequin"]
    adapter = _harlequin_adapter(resolved) if resolved else _harlequin_url_adapter(url) if url is not None else None
    if adapter is not None:
        command.extend(["--adapter", adapter])
    if read_only and (resolved or url is not None):
        command.append("--read-only")
    if theme is not None:
        command.extend(["--theme", theme])
    if limit is not None:
        command.extend(["--limit", str(limit)])
    if url is not None:
        command.append(url)
    command.extend(str(path) for path in resolved)
    return command


def _launch_interactive_command(command: list[str]) -> None:
    import shutil
    import subprocess

    executable = command[0]
    if shutil.which(executable) is None:
        raise FileNotFoundError(f"Command not found: {executable}")
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise typer.Exit(code=completed.returncode)


def _validate_backend(backend: BACKEND, resolved: list[Path]) -> None:
    is_all_duckdb = all(path.suffix.lower() in DUCKDB_EXTS for path in resolved)
    if is_all_duckdb and backend not in DUCKDB_CAPABLE:
        duckdb_capable_list = ", ".join(sorted(DUCKDB_CAPABLE))
        raise ValueError(
            f"Backend '{backend}' does not support DuckDB files.\n"
            f"DuckDB-capable backends: {duckdb_capable_list}\n"
            f"Files: {[str(path) for path in resolved]}"
        )
    if len(resolved) > 1 and backend not in MULTI_DB_CAPABLE:
        multi_capable_list = ", ".join(sorted(MULTI_DB_CAPABLE))
        raise ValueError(
            f"Backend '{backend}' cannot open multiple files simultaneously.\n"
            f"Multi-file-capable backends: {multi_capable_list}\n"
            f"Files ({len(resolved)}): {[str(path) for path in resolved]}"
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


def _resolve_paths(path: str | None, url: str | None, find: str | None, find_root: str | None, recursive: bool) -> list[Path]:
    if sum(option is not None for option in (path, url, find)) > 1:
        raise ValueError("Provide only one of `path`, `url`, or `find`.")
    if path is not None:
        if _looks_like_url(path):
            raise ValueError("Database connection URLs must be passed with `--url` or `-u`, not as the positional `path`.")
        return [Path(path).expanduser().resolve()]
    if url is not None:
        if not _looks_like_url(url):
            raise ValueError("The value passed to `--url` / `-u` must be a database connection URL.")
        return []
    if find is None:
        return []
    root = Path(find_root).expanduser().resolve() if find_root is not None else Path.cwd()
    resolved = _find_files(find, root, recursive)
    if not resolved:
        raise FileNotFoundError(f"No files matched pattern '{find}' under '{root}' (recursive={recursive})")
    print(f"Found {len(resolved)} file(s) matching '{find}' under '{root}'")
    return resolved


def _build_command(
    backend: BACKEND,
    resolved: list[Path],
    url: str | None,
    read_only: bool,
    theme: str | None,
    limit: int | None,
) -> list[str]:
    match backend:
        case "rainfrog":
            return _rainfrog_command(resolved[0] if resolved else None, url=url, read_only=read_only)
        case "lazysql":
            command = ["lazysql"]
            if read_only:
                command.append("-read-only")
            if url is not None:
                command.append(url)
            elif resolved:
                command.append(_url_for(resolved[0]))
            return command
        case "dblab":
            command = ["dblab"]
            if limit is not None:
                command.extend(["--limit", str(limit)])
            if url is not None:
                command.extend(["--url", url])
            elif resolved:
                command.extend(["--url", _url_for(resolved[0])])
            return command
        case "usql":
            command = ["usql"]
            if url is not None:
                command.append(url)
            elif resolved:
                command.append(_url_for(resolved[0]))
            return command
        case "harlequin":
            return _harlequin_command(resolved=resolved, url=url, read_only=read_only, theme=theme, limit=limit)
        case "sqlit":
            command = ["sqlit"]
            if theme is not None:
                command.extend(["--theme", theme])
            if limit is not None:
                command.extend(["--max-rows", str(limit)])
            if url is not None:
                command.append(url)
            elif resolved:
                command.append(_url_for(resolved[0]))
            return command


def normalize_backend(backend: BACKEND_LOOSE) -> BACKEND:
    return LOOSE_TO_STRICT[backend]


def build_read_db_cli_tui_command(
    path: str | None = None,
    url: str | None = None,
    find: str | None = None,
    find_root: str | None = None,
    recursive: bool = False,
    backend: BACKEND_LOOSE = "harlequin",
    read_only: bool = True,
    theme: str | None = None,
    limit: int | None = None,
) -> list[str]:
    backend_strict = normalize_backend(backend)
    resolved = _resolve_paths(path=path, url=url, find=find, find_root=find_root, recursive=recursive)
    if resolved:
        _validate_backend(backend_strict, resolved)
        _validate_read_only_support(backend_strict, read_only, resolved)
    return _build_command(
        backend=backend_strict,
        resolved=resolved,
        url=url,
        read_only=read_only,
        theme=theme,
        limit=limit,
    )


def run_read_db_cli_tui(
    path: str | None = None,
    url: str | None = None,
    find: str | None = None,
    find_root: str | None = None,
    recursive: bool = False,
    backend: BACKEND_LOOSE = "harlequin",
    read_only: bool = True,
    theme: str | None = None,
    limit: int | None = None,
) -> None:
    backend_strict = normalize_backend(backend)
    command = build_read_db_cli_tui_command(
        path=path,
        url=url,
        find=find,
        find_root=find_root,
        recursive=recursive,
        backend=backend,
        read_only=read_only,
        theme=theme,
        limit=limit,
    )
    _print_built_command(command)
    if backend_strict == "harlequin" and url is not None:
        _validate_harlequin_url_adapter(url=url)
    _launch_interactive_command(command)
