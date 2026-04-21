from pathlib import Path

import pytest

from stackops.settings.yazi.scripts import fullscreen_preview


def test_build_markdown_command_uses_more_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_path = tmp_path.joinpath("notes.md")
    target_path.write_text("# Notes\n", encoding="utf-8")

    def fake_system() -> str:
        return "Windows"

    monkeypatch.setattr(fullscreen_preview.platform, "system", fake_system)

    command = fullscreen_preview.build_command(target_path=target_path, terminal_columns=122)

    assert command == [
        "powershell",
        "-NoLogo",
        "-NoProfile",
        "-Command",
        "$env:CLICOLOR_FORCE='1'; glow --width $args[0] --style dark -- $args[1] | more.com",
        "--",
        "122",
        str(target_path),
    ]


@pytest.mark.parametrize("file_name", ["notes.md", "notes.markdown"])
def test_build_markdown_command_uses_glow_pager_on_unix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    file_name: str,
) -> None:
    target_path = tmp_path.joinpath(file_name)
    target_path.write_text("# Notes\n", encoding="utf-8")

    def fake_system() -> str:
        return "Linux"

    monkeypatch.setattr(fullscreen_preview.platform, "system", fake_system)

    command = fullscreen_preview.build_command(target_path=target_path, terminal_columns=122)

    assert command == ["glow", "--pager", "--width", "122", "--style", "dark", str(target_path)]
