from pathlib import Path
import sys

import pytest

from stackops.settings.yazi.scripts import interactive_view


@pytest.mark.parametrize("file_name", ["report.html", "report.pdf", "photo.jpg", "diagram.svg", "scan.webp"])
def test_build_command_routes_browser_files_to_browser_server(tmp_path: Path, file_name: str) -> None:
    target_path = tmp_path.joinpath(file_name)
    if target_path.suffix == ".pdf":
        target_path.write_bytes(b"%PDF-1.7\n")
    elif target_path.suffix in {".jpg", ".webp"}:
        target_path.write_bytes(b"image")
    else:
        target_path.write_text("<!doctype html>", encoding="utf-8")

    command = interactive_view.build_command(target_path=target_path)

    assert command == [sys.executable, str(Path(interactive_view.__file__).with_name("serve_browser_file.py")), str(target_path)]


@pytest.mark.parametrize("file_name", ["notes.md", "notes.markdown"])
def test_build_command_routes_markdown_to_glow_tui(tmp_path: Path, file_name: str) -> None:
    target_path = tmp_path.joinpath(file_name)
    target_path.write_text("# Notes\n", encoding="utf-8")

    command = interactive_view.build_command(target_path=target_path)

    assert command == ["glow", "--tui", str(target_path)]


def test_build_command_routes_directory_to_browser_server(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("gallery")
    target_path.mkdir()

    command = interactive_view.build_command(target_path=target_path)

    assert command == [sys.executable, str(Path(interactive_view.__file__).with_name("serve_browser_file.py")), str(target_path)]
