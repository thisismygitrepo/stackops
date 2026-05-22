from pathlib import Path
import platform
import subprocess
import sys
from typing import Literal


type ClipboardBackend = Literal[
    "cb",
    "wl-copy",
    "xclip",
    "xsel",
    "pbcopy",
    "clip.exe",
    "powershell-set-clipboard",
]


def _clipboard_commands() -> list[tuple[ClipboardBackend, list[str]]]:
    system_name = platform.system()
    if system_name == "Windows":
        return [
            ("cb", ["cb", "cp0"]),
            ("clip.exe", ["clip.exe"]),
            (
                "powershell-set-clipboard",
                ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", "Set-Clipboard"],
            ),
        ]

    if system_name == "Darwin":
        return [
            ("cb", ["cb", "cp0"]),
            ("pbcopy", ["pbcopy"]),
        ]

    return [
        ("cb", ["cb", "cp0"]),
        ("wl-copy", ["wl-copy"]),
        ("xclip", ["xclip", "-selection", "clipboard"]),
        ("xsel", ["xsel", "--clipboard", "--input"]),
    ]


def _copy_with_backend(content: bytes, command: list[str]) -> str | None:
    try:
        subprocess.run(command, input=content, check=True)
    except FileNotFoundError as error:
        return str(error)
    except subprocess.CalledProcessError as error:
        return str(error)

    return None


def _copy_to_clipboard(content: bytes) -> None:
    failures: list[str] = []
    for backend_name, command in _clipboard_commands():
        error = _copy_with_backend(content, command)
        if error is None:
            return
        failures.append(f"{backend_name}: {error}")

    failure_message = "\n".join(failures)
    raise SystemExit(f"No clipboard backend succeeded.\n{failure_message}")


def main() -> int:
    argv: list[str] = sys.argv
    if len(argv) != 2:
        raise SystemExit("Expected exactly one path argument.")

    path = Path(argv[1]).expanduser()
    if not path.is_file():
        raise SystemExit(f"Expected a file, got: {path}")

    _copy_to_clipboard(path.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
