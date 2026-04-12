from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from machineconfig.settings.yazi.scripts import interactive_view


def test_resolve_target_prefers_single_selected_file_over_hovered_file(tmp_path: Path) -> None:
    hovered_path = tmp_path.joinpath("hovered.csv")
    hovered_path.write_text("hovered", encoding="utf-8")
    selected_path = tmp_path.joinpath("selected.csv")
    selected_path.write_text("selected", encoding="utf-8")

    resolved_path = interactive_view.resolve_target(
        [interactive_view.HOVERED_MARKER, str(hovered_path), interactive_view.SELECTED_MARKER, str(selected_path)]
    )

    assert resolved_path == selected_path.resolve()


def test_build_command_uses_wrap_mcfg_for_csv_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("table.csv")
    target_path.write_text("a,b\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(interactive_view.Path, "home", lambda: Path("/home/tester"))

    command = interactive_view.build_command(target_path=target_path)

    assert command == ["/home/tester/.config/machineconfig/scripts/wrap_mcfg", "croshell", "-b", "v", str(target_path)]


@pytest.mark.parametrize(
    ("builder", "expected_code", "expected_message"),
    [
        (
            lambda tmp_path: [
                interactive_view.HOVERED_MARKER,
                interactive_view.SELECTED_MARKER,
                str(tmp_path.joinpath("one.csv")),
                str(tmp_path.joinpath("two.csv")),
            ],
            1,
            "Interactive view requires exactly one selected file.",
        ),
        (
            lambda tmp_path: [
                interactive_view.HOVERED_MARKER,
                str(tmp_path.joinpath("hovered.csv")),
                interactive_view.SELECTED_MARKER,
                str(tmp_path.joinpath("selected.csv")),
            ],
            127,
            "wrap_mcfg",
        ),
    ],
)
def test_main_maps_runtime_errors_to_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    builder: Callable[[Path], list[str]],
    expected_code: int,
    expected_message: str,
) -> None:
    hovered_path = tmp_path.joinpath("hovered.csv")
    hovered_path.write_text("x", encoding="utf-8")
    selected_path = tmp_path.joinpath("selected.csv")
    selected_path.write_text("x", encoding="utf-8")

    def fake_exec_command(command: Sequence[str]) -> None:
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(interactive_view, "exec_command", fake_exec_command)
    monkeypatch.setattr(interactive_view.Path, "home", lambda: Path("/home/tester"))

    exit_code = interactive_view.main(arguments=builder(tmp_path))

    assert exit_code == expected_code
    assert expected_message in capsys.readouterr().err
