from collections.abc import Sequence
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Final, NoReturn

type Command = list[str]

HOVERED_MARKER: Final[str] = "__YAZI_HOVERED__"
SELECTED_MARKER: Final[str] = "__YAZI_SELECTED__"
ARCHIVE_SUFFIXES: Final[tuple[str, ...]] = (
    ".7z",
    ".bz2",
    ".gz",
    ".jar",
    ".rar",
    ".tar",
    ".tar.bz2",
    ".tar.gz",
    ".tar.xz",
    ".tar.zst",
    ".tgz",
    ".txz",
    ".xz",
    ".zip",
    ".zst",
)
SQLITE_SUFFIXES: Final[frozenset[str]] = frozenset({".db", ".db3", ".s3db", ".sl3", ".sqlite", ".sqlite3"})
VISIDATA_SUFFIXES: Final[frozenset[str]] = frozenset({".parquet", ".tsv", ".xlsx"})


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
    if hovered_path is not None:
        return Path(hovered_path).resolve()
    if len(selected_paths) == 1:
        return Path(selected_paths[0]).resolve()
    if selected_paths:
        raise ValueError("Standalone fullscreen preview requires a single target.")
    raise ValueError("No hovered file or selected file was provided.")


def is_archive_path(target_path: Path) -> bool:
    name = target_path.name.lower()
    return any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def build_archive_command(target_path: Path) -> Command:
    if platform.system().lower() == "windows":
        return [
            "powershell",
            "-NoLogo",
            "-NoProfile",
            "-Command",
            "ouch list -- $args[0] | more.com",
            "--",
            str(target_path),
        ]
    return ["sh", "-c", 'ouch list "$1" | ${PAGER:-less -R}', "sh", str(target_path)]


def build_command(target_path: Path, terminal_columns: int) -> Command:
    if not target_path.is_file():
        raise ValueError(f"Standalone fullscreen preview requires a file, got: {target_path}")
    suffix = target_path.suffix.lower()
    path_string = str(target_path)
    match suffix:
        case ".md":
            return ["glow", "--pager", "--width", str(terminal_columns), "--style", "dark", path_string]
        case ".csv":
            return [
                "uvx",
                "--from",
                "rich-cli",
                "rich",
                "--force-terminal",
                "--csv",
                "--pager",
                "--width",
                str(terminal_columns),
                path_string,
            ]
        case ".json" | ".jsonl" | ".ndjson":
            return [
                "uvx",
                "--from",
                "rich-cli",
                "rich",
                "--force-terminal",
                "--json",
                "--pager",
                "--width",
                str(terminal_columns),
                path_string,
            ]
        case ".duckdb":
            return ["rainfrog", "--driver", "duckdb", "--database", path_string]
        case _ if suffix in SQLITE_SUFFIXES:
            return ["rainfrog", "--driver", "sqlite", "--database", path_string]
        case _ if suffix in VISIDATA_SUFFIXES:
            return ["uvx", "--from", "visidata", "--with", "pyarrow", "vd", path_string]
        case _ if is_archive_path(target_path):
            return build_archive_command(target_path)
        case _:
            return [
                "bat",
                "--paging=always",
                "--style=plain",
                "--color=always",
                "--terminal-width",
                str(terminal_columns),
                path_string,
            ]


def exec_command(command: Sequence[str]) -> NoReturn:
    os.execvp(command[0], list(command))


def main(arguments: Sequence[str]) -> int:
    try:
        target_path = resolve_target(arguments)
        terminal_columns = shutil.get_terminal_size(fallback=(120, 40)).columns
        command = build_command(target_path=target_path, terminal_columns=terminal_columns)
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
