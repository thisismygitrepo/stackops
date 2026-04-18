from __future__ import annotations

from collections.abc import Sequence

import pytest

from stackops.settings.yazi.scripts import compress_selected


def test_split_marked_arguments_extracts_hovered_and_selected_paths() -> None:
    hovered_path, selected_paths = compress_selected.split_marked_arguments(
        ["ignored", compress_selected.HOVERED_MARKER, "/tmp/hovered.txt", compress_selected.SELECTED_MARKER, "/tmp/first.txt", "/tmp/second.txt"]
    )

    assert hovered_path == "/tmp/hovered.txt"
    assert selected_paths == ["/tmp/first.txt", "/tmp/second.txt"]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["ignored"], "Missing Yazi argument markers."),
        ([compress_selected.SELECTED_MARKER, "/tmp/file.txt", compress_selected.HOVERED_MARKER], "Yazi argument markers are out of order."),
        ([compress_selected.HOVERED_MARKER, "/tmp/a.txt", "/tmp/b.txt", compress_selected.SELECTED_MARKER], "Expected at most one hovered path."),
    ],
)
def test_split_marked_arguments_rejects_invalid_marker_layout(arguments: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        compress_selected.split_marked_arguments(arguments)


def test_resolve_targets_prefers_selected_paths_over_hovered_path() -> None:
    targets = compress_selected.resolve_targets(
        [compress_selected.HOVERED_MARKER, "/tmp/hovered.txt", compress_selected.SELECTED_MARKER, "/tmp/selected.txt"]
    )

    assert targets == ["/tmp/selected.txt"]


def test_build_command_uses_working_directory_name_for_multi_file_archive() -> None:
    command = compress_selected.build_command(
        arguments=[compress_selected.HOVERED_MARKER, compress_selected.SELECTED_MARKER, "/tmp/one.txt", "/tmp/two.txt"],
        working_directory="/tmp/workspace",
    )

    assert command == ["ouch", "compress", "/tmp/one.txt", "/tmp/two.txt", "/tmp/workspace/workspace.zip"]


def test_main_maps_runtime_failures_to_exit_codes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    bad_arguments_exit_code = compress_selected.main(arguments=["missing-markers"])

    assert bad_arguments_exit_code == 1
    assert "Missing Yazi argument markers." in capsys.readouterr().err

    observed_command: list[str] = []

    def fake_exec_command(command: Sequence[str]) -> None:
        observed_command.extend(command)
        raise FileNotFoundError("ouch")

    monkeypatch.setattr(compress_selected, "exec_command", fake_exec_command)

    missing_tool_exit_code = compress_selected.main(
        arguments=[compress_selected.HOVERED_MARKER, "/tmp/hovered.txt", compress_selected.SELECTED_MARKER]
    )

    assert missing_tool_exit_code == 127
    assert observed_command == ["ouch", "compress", "/tmp/hovered.txt", "/tmp/hovered.txt.zip"]
    assert "ouch" in capsys.readouterr().err
