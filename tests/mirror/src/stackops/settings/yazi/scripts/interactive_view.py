from pathlib import Path
import sys

import pytest

from stackops.settings.yazi.scripts import interactive_view


@pytest.mark.parametrize("file_name", ["report.html", "report.pdf"])
def test_build_command_routes_browser_files_to_browser_server(tmp_path: Path, file_name: str) -> None:
    target_path = tmp_path.joinpath(file_name)
    if target_path.suffix == ".pdf":
        target_path.write_bytes(b"%PDF-1.7\n")
    else:
        target_path.write_text("<!doctype html>", encoding="utf-8")

    command = interactive_view.build_command(target_path=target_path)

    assert command == [sys.executable, str(Path(interactive_view.__file__).with_name("serve_browser_file.py")), str(target_path)]
