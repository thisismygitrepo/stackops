from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.utils.path_core as path_core


def test_copy_to_same_path_uses_generated_copy_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("data.txt")
    source.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(path_core, "randstr", lambda: "token")

    result = path_core.copy(source, path=source, verbose=False)

    assert result == tmp_path.joinpath("data_copy_token.txt")
    assert result.read_text(encoding="utf-8") == "hello"


def test_collapseuser_rewrites_home_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    target = fake_home.joinpath("docs", "note.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")

    monkeypatch.setattr(path_core, "_home_path", lambda: fake_home)

    collapsed = path_core.collapseuser(target)

    assert str(collapsed) == "~/docs/note.txt"


def test_with_name_inplace_overwrites_existing_destination(tmp_path: Path) -> None:
    source = tmp_path.joinpath("before.txt")
    destination = tmp_path.joinpath("after.txt")
    source.write_text("source", encoding="utf-8")
    destination.write_text("destination", encoding="utf-8")

    result = path_core.with_name(source, name="after.txt", inplace=True, overwrite=True, verbose=False)

    assert result == destination
    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "source"


def test_move_moves_file_to_folder(tmp_path: Path) -> None:
    source = tmp_path.joinpath("data.txt")
    source.write_text("hello", encoding="utf-8")
    destination_folder = tmp_path.joinpath("out")

    result = path_core.move(source, folder=destination_folder, overwrite=False, verbose=False)

    assert result == destination_folder.resolve().joinpath("data.txt")
    assert not source.exists()
    assert result.read_text(encoding="utf-8") == "hello"


def test_resolve_returns_original_path_when_strict_resolution_fails(tmp_path: Path) -> None:
    target = tmp_path.joinpath("missing.txt")
    broken_link = tmp_path.joinpath("broken-link")
    try:
        broken_link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks are not available in this environment.")

    resolved = path_core.resolve(broken_link, strict=True)

    assert resolved == broken_link
