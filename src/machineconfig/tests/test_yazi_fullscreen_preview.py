from pathlib import Path

import pytest

from machineconfig.settings.yazi.scripts import fullscreen_preview


def test_describe_command_includes_action_tool_and_command() -> None:
    description = fullscreen_preview.describe_command(
        action="Display preview image",
        command=["viu", "/tmp/example.png"],
    )

    assert description == (
        "[yazi preview] action: Display preview image\n"
        "[yazi preview] tool: viu\n"
        "[yazi preview] command: viu /tmp/example.png\n"
    )


def test_build_pdf_text_command_uses_pdftotext(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("example.pdf")
    target_path.write_bytes(b"%PDF-1.4\n")
    output_path = tmp_path.joinpath("preview.txt")

    command = fullscreen_preview.build_pdf_text_command(
        target_path=target_path,
        output_path=output_path,
    )

    assert command == [
        "pdftotext",
        "-layout",
        "-nopgbrk",
        "-q",
        "--",
        str(target_path),
        str(output_path),
    ]


def test_build_command_uses_viu_for_images(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("example.png")
    target_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    command = fullscreen_preview.build_command(
        target_path=target_path,
        terminal_columns=120,
    )

    assert command == ["viu", str(target_path)]


def test_build_pager_command_uses_less_on_unix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fullscreen_preview.platform, "system", lambda: "Darwin")

    command = fullscreen_preview.build_pager_command()

    assert command == ["less", "-R"]


def test_should_wait_for_return_only_for_viu() -> None:
    assert fullscreen_preview.should_wait_for_return(["viu", "/tmp/example.png"]) is True
    assert fullscreen_preview.should_wait_for_return(["bat", "/tmp/example.txt"]) is False


def test_preview_target_routes_pdf_to_pdf_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_path = tmp_path.joinpath("example.pdf")
    target_path.write_bytes(b"%PDF-1.4\n")
    captured: dict[str, Path] = {}

    def fake_run_pdf_preview(*, target_path: Path) -> int:
        captured["target_path"] = target_path
        return 17

    monkeypatch.setattr(fullscreen_preview, "run_pdf_preview", fake_run_pdf_preview)

    exit_code = fullscreen_preview.preview_target(
        target_path=target_path,
        terminal_columns=88,
    )

    assert exit_code == 17
    assert captured["target_path"] == target_path


def test_preview_target_keeps_standard_mode_behavior_for_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target_path = tmp_path.joinpath("example.txt")
    target_path.write_text("hello\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run_command(*, command: fullscreen_preview.Command, action: str) -> int:
        captured["command"] = command
        captured["action"] = action
        return 0

    monkeypatch.setattr(fullscreen_preview, "run_command", fake_run_command)

    exit_code = fullscreen_preview.preview_target(
        target_path=target_path,
        terminal_columns=88,
    )

    assert exit_code == 0
    assert captured["command"] == [
        "bat",
        "--paging=always",
        "--style=plain",
        "--color=always",
        "--terminal-width",
        "88",
        str(target_path),
    ]
    assert captured["action"] == "Preview target file"
