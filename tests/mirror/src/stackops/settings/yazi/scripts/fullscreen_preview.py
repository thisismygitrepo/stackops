

import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from stackops.settings.yazi.scripts import fullscreen_preview


def test_resolve_target_prefers_hovered_path_over_selected_path(tmp_path: Path) -> None:
    hovered_path = tmp_path.joinpath("hovered.txt")
    hovered_path.write_text("hovered", encoding="utf-8")
    selected_path = tmp_path.joinpath("selected.txt")
    selected_path.write_text("selected", encoding="utf-8")

    resolved_path = fullscreen_preview.resolve_target(
        [fullscreen_preview.HOVERED_MARKER, str(hovered_path), fullscreen_preview.SELECTED_MARKER, str(selected_path)]
    )

    assert resolved_path == hovered_path.resolve()


@pytest.mark.parametrize(
    ("filename", "expected_command"),
    [
        ("notes.md", ["glow", "--pager", "--width", "88", "--style", "dark"]),
        ("table.csv", ["uvx", "--from", "rich-cli", "rich", "--force-terminal", "--csv", "--pager", "--width", "88"]),
        ("records.json", ["uvx", "--from", "rich-cli", "rich", "--force-terminal", "--json", "--pager", "--width", "88"]),
        ("sheet.parquet", ["uvx", "--from", "visidata", "--with", "pyarrow", "vd"]),
        ("bundle.tar.gz", ["sh", "-c", 'ouch list "$1" | ${PAGER:-less -R}', "sh"]),
        ("image.png", ["viu"]),
        ("plain.txt", ["bat", "--paging=always", "--style=plain", "--color=always", "--terminal-width", "88"]),
    ],
)
def test_build_command_dispatches_by_suffix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, filename: str, expected_command: list[str]) -> None:
    monkeypatch.setattr(fullscreen_preview.platform, "system", lambda: "Linux")
    target_path = tmp_path.joinpath(filename)
    target_path.write_text("content", encoding="utf-8")

    command = fullscreen_preview.build_command(target_path=target_path, terminal_columns=88)

    assert command[:-1] == expected_command
    assert command[-1] == str(target_path)


def test_build_command_uses_read_only_harlequin_for_duckdb_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fullscreen_preview.platform, "system", lambda: "Linux")
    target_path = tmp_path.joinpath("warehouse.duckdb")
    target_path.write_text("content", encoding="utf-8")

    command = fullscreen_preview.build_command(target_path=target_path, terminal_columns=88)

    assert command == ["harlequin", "--adapter", "duckdb", "--read-only", str(target_path)]


def test_build_command_uses_read_only_rainfrog_url_for_sqlite_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fullscreen_preview.platform, "system", lambda: "Linux")
    target_path = tmp_path.joinpath("cache.sqlite3")
    target_path.write_text("content", encoding="utf-8")

    command = fullscreen_preview.build_command(target_path=target_path, terminal_columns=88)

    expected_url = f"""sqlite://{target_path.resolve().as_uri().removeprefix("file://")}?mode=ro"""
    assert command == ["rainfrog", "--url", expected_url]


def test_platform_specific_archive_and_pager_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    archive_path = Path("/tmp/archive.zip")

    monkeypatch.setattr(fullscreen_preview.platform, "system", lambda: "Windows")
    assert fullscreen_preview.build_archive_command(target_path=archive_path) == [
        "powershell",
        "-NoLogo",
        "-NoProfile",
        "-Command",
        "ouch list -- $args[0] | more.com",
        "--",
        str(archive_path),
    ]
    assert fullscreen_preview.build_pager_command() == ["more.com"]

    monkeypatch.setattr(fullscreen_preview.platform, "system", lambda: "Linux")
    assert fullscreen_preview.build_archive_command(target_path=archive_path) == [
        "sh",
        "-c",
        'ouch list "$1" | ${PAGER:-less -R}',
        "sh",
        str(archive_path),
    ]
    assert fullscreen_preview.build_pager_command() == ["less", "-R"]


def test_preview_target_dispatches_pdf_svg_and_generic_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = tmp_path.joinpath("doc.pdf")
    pdf_path.write_text("pdf", encoding="utf-8")
    svg_path = tmp_path.joinpath("image.svg")
    svg_path.write_text("<svg />", encoding="utf-8")
    text_path = tmp_path.joinpath("notes.txt")
    text_path.write_text("notes", encoding="utf-8")

    calls: list[tuple[str, Path | Sequence[str]]] = []

    def fake_run_pdf_preview(target_path: Path) -> int:
        calls.append(("pdf", target_path))
        return 11

    def fake_run_svg_preview(target_path: Path) -> int:
        calls.append(("svg", target_path))
        return 22

    def fake_build_command(target_path: Path, terminal_columns: int) -> list[str]:
        assert terminal_columns == 91
        return ["bat", str(target_path)]

    def fake_run_command(command: Sequence[str], action: str) -> int:
        assert action == "Preview target file"
        calls.append(("generic", list(command)))
        return 33

    monkeypatch.setattr(fullscreen_preview, "run_pdf_preview", fake_run_pdf_preview)
    monkeypatch.setattr(fullscreen_preview, "run_svg_preview", fake_run_svg_preview)
    monkeypatch.setattr(fullscreen_preview, "build_command", fake_build_command)
    monkeypatch.setattr(fullscreen_preview, "run_command", fake_run_command)

    assert fullscreen_preview.preview_target(target_path=pdf_path, terminal_columns=91) == 11
    assert fullscreen_preview.preview_target(target_path=svg_path, terminal_columns=91) == 22
    assert fullscreen_preview.preview_target(target_path=text_path, terminal_columns=91) == 33
    assert calls == [("pdf", pdf_path), ("svg", svg_path), ("generic", ["bat", str(text_path)])]


def test_run_rendered_image_preview_requires_render_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    render_calls: list[tuple[list[str], str]] = []
    render_command = ["resvg", "input.svg", "preview.png"]
    rendered_image_path = tmp_path.joinpath("preview.png")

    def fake_run_command(command: Sequence[str], action: str) -> int:
        render_calls.append((list(command), action))
        return 0

    monkeypatch.setattr(fullscreen_preview, "run_command", fake_run_command)

    with pytest.raises(FileNotFoundError, match="Expected rendered preview image"):
        fullscreen_preview.run_rendered_image_preview(render_command=render_command, rendered_image_path=rendered_image_path)

    assert render_calls == [(render_command, "Render preview image")]


@pytest.mark.parametrize(("error", "expected_code"), [(ValueError("bad markers"), 1), (FileNotFoundError("missing tool"), 127)])
def test_main_maps_errors_to_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error: Exception, expected_code: int
) -> None:
    def fake_resolve_target(arguments: Sequence[str]) -> Path:
        raise error

    monkeypatch.setattr(fullscreen_preview, "resolve_target", fake_resolve_target)
    monkeypatch.setattr(fullscreen_preview.shutil, "get_terminal_size", lambda fallback: os.terminal_size((120, 40)))

    exit_code = fullscreen_preview.main(arguments=[])

    assert exit_code == expected_code
    assert str(error) in capsys.readouterr().err
