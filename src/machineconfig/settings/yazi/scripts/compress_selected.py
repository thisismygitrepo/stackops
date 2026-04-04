from collections.abc import Sequence
import os
import sys
from typing import NoReturn

HOVERED_MARKER = "__YAZI_HOVERED__"
SELECTED_MARKER = "__YAZI_SELECTED__"


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


def resolve_targets(arguments: Sequence[str]) -> list[str]:
    hovered_path, selected_paths = split_marked_arguments(arguments)
    if selected_paths:
        return selected_paths
    if hovered_path:
        return [hovered_path]
    raise ValueError("No hovered file or selected files were provided.")


def build_archive_path(target_paths: Sequence[str], working_directory: str) -> str:
    if len(target_paths) == 1:
        return f"{target_paths[0]}.zip"
    archive_name = os.path.basename(os.path.normpath(working_directory)) or "archive"
    return os.path.join(working_directory, f"{archive_name}.zip")


def build_command(arguments: Sequence[str], working_directory: str) -> list[str]:
    target_paths = resolve_targets(arguments)
    archive_path = build_archive_path(target_paths=target_paths, working_directory=working_directory)
    return ["ouch", "compress", *target_paths, archive_path]


def exec_command(command: Sequence[str]) -> NoReturn:
    os.execvp(command[0], list(command))


def main(arguments: Sequence[str]) -> int:
    try:
        command = build_command(arguments=arguments, working_directory=os.getcwd())
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
