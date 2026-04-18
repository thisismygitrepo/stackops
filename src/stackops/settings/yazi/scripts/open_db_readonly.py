from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import Final, NoReturn

DUCKDB_SUFFIXES: Final[frozenset[str]] = frozenset({".duckdb", ".ddb"})
SQLITE_SUFFIXES: Final[frozenset[str]] = frozenset({".db", ".db3", ".s3db", ".sl3", ".sqlite", ".sqlite3"})


def sql_string(value: str) -> str:
    return f"""'{value.replace("'", "''")}'"""


def build_attach_statement(target_path: Path) -> str:
    quoted_path = sql_string(str(target_path))
    if target_path.suffix.lower() in SQLITE_SUFFIXES:
        return f"""ATTACH {quoted_path} AS data (READ_ONLY, TYPE SQLITE); USE data;"""
    return f"""ATTACH {quoted_path} AS data (READ_ONLY); USE data;"""


def get_ui_catalog_path() -> Path:
    return Path.home().joinpath(".cache", "stackops", "yazi", "duckdb-ui-catalog.duckdb")


def build_command(target_path: Path, launch_ui: bool) -> list[str]:
    if not target_path.is_file():
        raise ValueError(f"Expected a database file, got: {target_path}")
    suffix = target_path.suffix.lower()
    if suffix in DUCKDB_SUFFIXES:
        if launch_ui:
            return ["duckdb", "-ui", "-cmd", build_attach_statement(target_path=target_path), str(get_ui_catalog_path())]
        return ["duckdb", "-readonly", str(target_path)]
    if suffix in SQLITE_SUFFIXES:
        if launch_ui:
            return ["duckdb", "-ui", "-cmd", build_attach_statement(target_path=target_path), str(get_ui_catalog_path())]
        return ["duckdb", "-cmd", build_attach_statement(target_path=target_path), ":memory:"]
    raise ValueError(f"Unsupported database extension: {target_path.suffix or 'none'}")


def parse_arguments(arguments: Sequence[str]) -> tuple[Path, bool]:
    launch_ui = False
    positional_arguments: list[str] = []
    for argument in arguments:
        if argument == "--ui":
            launch_ui = True
            continue
        positional_arguments.append(argument)
    if len(positional_arguments) != 1:
        raise ValueError("Usage: open_db_readonly.py [--ui] <database-path>")
    return Path(positional_arguments[0]).resolve(), launch_ui


def exec_command(command: list[str]) -> NoReturn:
    executable = command[0]
    remaining_arguments = tuple(command[1:])
    os.execlp(executable, executable, *remaining_arguments)


def main(arguments: Sequence[str]) -> int:
    try:
        target_path, launch_ui = parse_arguments(arguments=arguments)
        if launch_ui:
            get_ui_catalog_path().parent.mkdir(parents=True, exist_ok=True)
        command = build_command(target_path=target_path, launch_ui=launch_ui)
        exec_command(command)
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 127


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
