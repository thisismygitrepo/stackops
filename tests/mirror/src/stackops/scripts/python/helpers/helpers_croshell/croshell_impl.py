import os
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_croshell import croshell_impl


def test_auto1_backend_reuses_fullscreen_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target_path = tmp_path.joinpath("preview.txt")
    target_path.write_text("hello", encoding="utf-8")
    captured: dict[str, Path | int] = {}

    monkeypatch.setattr(
        "stackops.utils.path_helper.get_choice_file",
        lambda *, path, suffixes, search_root: target_path,
    )
    monkeypatch.setattr(
        croshell_impl.shutil,
        "get_terminal_size",
        lambda fallback=(120, 40): os.terminal_size((144, 50)),
    )

    def fake_preview_target(*, target_path: Path, terminal_columns: int) -> int:
        captured["target_path"] = target_path
        captured["terminal_columns"] = terminal_columns
        return 0

    monkeypatch.setattr("stackops.settings.yazi.scripts.fullscreen_preview.preview_target", fake_preview_target)

    croshell_impl.croshell(
        path=str(target_path),
        project_path=None,
        uv_with=None,
        backend="auto1",
        profile=None,
        frozen=False,
    )

    assert captured == {"target_path": target_path, "terminal_columns": 144}


def test_auto2_backend_reuses_interactive_view(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target_path = tmp_path.joinpath("preview.csv")
    target_path.write_text("a,b\n1,2\n", encoding="utf-8")
    captured: dict[str, Path | list[str]] = {}

    monkeypatch.setattr(
        "stackops.utils.path_helper.get_choice_file",
        lambda *, path, suffixes, search_root: target_path,
    )

    def fake_build_command(*, target_path: Path) -> list[str]:
        captured["target_path"] = target_path
        return ["viewer", str(target_path)]

    def fake_exec_command(command: list[str]) -> None:
        captured["command"] = command

    monkeypatch.setattr("stackops.settings.yazi.scripts.interactive_view.build_command", fake_build_command)
    monkeypatch.setattr("stackops.settings.yazi.scripts.interactive_view.exec_command", fake_exec_command)

    croshell_impl.croshell(
        path=str(target_path),
        project_path=None,
        uv_with=None,
        backend="auto2",
        profile=None,
        frozen=False,
    )

    assert captured == {"target_path": target_path, "command": ["viewer", str(target_path)]}


def test_auto2_backend_can_force_database_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target_path = tmp_path.joinpath("preview.sqlite")
    target_path.write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "stackops.utils.path_helper.get_choice_file",
        lambda *, path, suffixes, search_root: target_path,
    )

    def fake_build_command(*, target_path: Path, mode: str, database_backend: str) -> list[str]:
        captured["target_path"] = target_path
        captured["mode"] = mode
        captured["database_backend"] = database_backend
        return ["viewer", str(target_path)]

    def fake_exec_command(command: list[str]) -> None:
        captured["command"] = command

    monkeypatch.setattr("stackops.settings.yazi.scripts.interactive_view.build_command", fake_build_command)
    monkeypatch.setattr("stackops.settings.yazi.scripts.interactive_view.exec_command", fake_exec_command)

    croshell_impl.croshell(
        path=str(target_path),
        project_path=None,
        uv_with=None,
        backend="auto2",
        profile=None,
        frozen=False,
        auto2_mode="database",
        auto2_db_backend="usql",
    )

    assert captured == {
        "target_path": target_path,
        "mode": "database",
        "database_backend": "usql",
        "command": ["viewer", str(target_path)],
    }


def test_auto_backends_require_a_path() -> None:
    with pytest.raises(ValueError, match="Auto preview backends require a path."):
        croshell_impl.croshell(
            path=None,
            project_path=None,
            uv_with=None,
            backend="auto1",
            profile=None,
            frozen=False,
        )
