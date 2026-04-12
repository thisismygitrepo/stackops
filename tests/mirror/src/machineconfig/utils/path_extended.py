from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.utils.path_extended as path_extended


def test_validate_name_replaces_disallowed_characters() -> None:
    assert path_extended.validate_name("bad name:/?.txt") == "bad_name_.txt"


def test_copy_to_same_path_uses_generated_copy_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("data.txt")
    source.write_text("hello", encoding="utf-8")

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "token"

    monkeypatch.setattr(path_extended, "randstr", fake_randstr)

    result = path_extended.PathExtended(source).copy(
        path=path_extended.PathExtended(source),
        verbose=False,
    )

    assert result == path_extended.PathExtended(tmp_path.joinpath("data_copy_token.txt"))
    assert Path(result).read_text(encoding="utf-8") == "hello"


def test_split_appends_separator_to_right_side() -> None:
    left, right = path_extended.PathExtended("root/alpha/beta").split(at="alpha", sep=1)

    assert str(left) == "root"
    assert str(right) == "alpha/beta"


def test_collapseuser_rewrites_home_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = path_extended.PathExtended(tmp_path.joinpath("home"))
    target = fake_home.joinpath("docs", "note.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")

    def fake_home_method(_cls: type[path_extended.PathExtended]) -> path_extended.PathExtended:
        return fake_home

    monkeypatch.setattr(path_extended.PathExtended, "home", classmethod(fake_home_method))

    collapsed = path_extended.PathExtended(target).collapseuser()

    assert str(collapsed) == "~/docs/note.txt"
