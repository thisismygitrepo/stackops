from collections.abc import Sequence
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Final, cast

type Command = list[str]

HOVERED_MARKER: Final[str] = "__YAZI_HOVERED__"
SELECTED_MARKER: Final[str] = "__YAZI_SELECTED__"
PDF_SUFFIX: Final[str] = ".pdf"
SVG_SUFFIX: Final[str] = ".svg"
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
VISIDATA_SUFFIXES: Final[frozenset[str]] = frozenset({".parquet", ".tsv", ".xlsx", ".csv", ".db", ".db3", ".s3db", ".sl3", ".sqlite", ".sqlite3"})
IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset({
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
})


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


def build_image_command(target_path: Path) -> Command:
    return ["viu", str(target_path)]


def build_pdf_text_command(target_path: Path, output_path: Path) -> Command:
    return ["pdftotext", "-layout", "-nopgbrk", "-q", "--", str(target_path), str(output_path)]


def build_pager_command() -> Command:
    if platform.system().lower() == "windows":
        return ["more.com"]
    return ["less", "-R"]


def build_svg_render_command(target_path: Path, output_path: Path) -> Command:
    return ["resvg", str(target_path), str(output_path)]


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
        case _ if suffix in IMAGE_SUFFIXES:
            return build_image_command(target_path=target_path)
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


def format_command(command: Sequence[str]) -> str:
    tokens = list(command)
    if platform.system().lower() == "windows":
        return subprocess.list2cmdline(tokens)
    return shlex.join(tokens)


def describe_command(action: str, command: Sequence[str]) -> str:
    tool_name = Path(command[0]).name
    return (
        f"""[yazi preview] action: {action}\n"""
        f"""[yazi preview] tool: {tool_name}\n"""
        f"""[yazi preview] command: {format_command(command)}\n"""
    )


def emit_command_description(action: str, command: Sequence[str]) -> None:
    sys.stderr.write(describe_command(action=action, command=command))
    sys.stderr.flush()


def should_wait_for_return(command: Sequence[str]) -> bool:
    return Path(command[0]).name.lower() == "viu"


def read_exit_key() -> str:
    if platform.system().lower() == "windows":
        import msvcrt

        getch = cast(Callable[[], bytes], getattr(msvcrt, "getch"))
        pressed_key = getch()
        if pressed_key in {b"\x00", b"\xe0"}:
            _ = getch()
        return pressed_key.decode("latin-1")

    import termios
    import tty

    stdin_file_descriptor = sys.stdin.fileno()
    previous_terminal_state = termios.tcgetattr(stdin_file_descriptor)
    try:
        tty.setraw(stdin_file_descriptor)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(stdin_file_descriptor, termios.TCSADRAIN, previous_terminal_state)


def wait_for_return_to_yazi() -> None:
    if not sys.stdin.isatty():
        return
    sys.stderr.write("\n[yazi preview] press q or Esc to return to Yazi\n")
    sys.stderr.flush()
    while True:
        pressed_key = read_exit_key()
        if pressed_key.lower() == "q" or pressed_key == "\x1b":
            break


def run_command(command: Sequence[str], action: str) -> int:
    emit_command_description(action=action, command=command)
    completed_process = subprocess.run(list(command), check=False)
    if completed_process.returncode == 0 and should_wait_for_return(command):
        wait_for_return_to_yazi()
    return completed_process.returncode


def run_command_with_input(command: Sequence[str], action: str, input_path: Path) -> int:
    emit_command_description(action=action, command=command)
    with input_path.open("rb") as input_file:
        completed_process = subprocess.run(list(command), stdin=input_file, check=False)
    return completed_process.returncode


def run_rendered_image_preview(render_command: Sequence[str], rendered_image_path: Path) -> int:
    render_exit_code = run_command(command=render_command, action="Render preview image")
    if render_exit_code != 0:
        return render_exit_code
    if not rendered_image_path.is_file():
        raise FileNotFoundError(f"Expected rendered preview image at {rendered_image_path}")
    return run_command(
        command=build_image_command(target_path=rendered_image_path),
        action="Display preview image",
    )


def run_pdf_preview(target_path: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="machineconfig-yazi-preview-") as temp_dir:
        rendered_text_path = Path(temp_dir).joinpath("preview.txt")
        extract_exit_code = run_command(
            command=build_pdf_text_command(target_path=target_path, output_path=rendered_text_path),
            action="Extract PDF text",
        )
        if extract_exit_code != 0:
            return extract_exit_code
        if not rendered_text_path.is_file():
            raise FileNotFoundError(f"Expected rendered preview text at {rendered_text_path}")
        return run_command_with_input(
            command=build_pager_command(),
            action="Page PDF text",
            input_path=rendered_text_path,
        )


def run_svg_preview(target_path: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="machineconfig-yazi-preview-") as temp_dir:
        rendered_image_path = Path(temp_dir).joinpath("preview.png")
        return run_rendered_image_preview(
            render_command=build_svg_render_command(target_path=target_path, output_path=rendered_image_path),
            rendered_image_path=rendered_image_path,
        )


def preview_target(target_path: Path, terminal_columns: int) -> int:
    if not target_path.is_file():
        raise ValueError(f"Standalone fullscreen preview requires a file, got: {target_path}")
    suffix = target_path.suffix.lower()
    if suffix == PDF_SUFFIX:
        return run_pdf_preview(target_path=target_path)
    if suffix == SVG_SUFFIX:
        return run_svg_preview(target_path=target_path)
    return run_command(
        command=build_command(target_path=target_path, terminal_columns=terminal_columns),
        action="Preview target file",
    )


def main(arguments: Sequence[str]) -> int:
    try:
        target_path = resolve_target(arguments)
        terminal_columns = shutil.get_terminal_size(fallback=(120, 40)).columns
        return preview_target(target_path=target_path, terminal_columns=terminal_columns)
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 127


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
