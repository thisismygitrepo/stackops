from __future__ import annotations

from pathlib import Path

import pytest

import stackops.utils.path_helper as path_helper


def test_sanitize_path_maps_foreign_unix_home_to_current_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_home = tmp_path.joinpath("home")
    target = fake_home.joinpath("docs", "note.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")

    def fake_home_method(_cls: type[Path]) -> Path:
        return fake_home

    def fake_system() -> str:
        return "Linux"

    def fake_print(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(path_helper.Path, "home", classmethod(fake_home_method))
    monkeypatch.setattr(path_helper.platform, "system", fake_system)
    monkeypatch.setattr(path_helper.console, "print", fake_print)

    resolved = path_helper.sanitize_path("/home/other/docs/note.txt")

    assert resolved == target.resolve()


def test_find_scripts_skips_excluded_dirs_and_collects_partial_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skipped_dir = tmp_path.joinpath("ignored")
    skipped_dir.mkdir()
    skipped_dir.joinpath("target.py").write_text("", encoding="utf-8")

    named_match = tmp_path.joinpath("pkg", "target_tool.py")
    named_match.parent.mkdir(parents=True, exist_ok=True)
    named_match.write_text("", encoding="utf-8")

    partial_match = tmp_path.joinpath("withtarget", "module.py")
    partial_match.parent.mkdir(parents=True, exist_ok=True)
    partial_match.write_text("", encoding="utf-8")

    monkeypatch.setattr(path_helper, "EXCLUDE_DIRS", ("ignored",))

    filename_matches, partial_path_matches = path_helper.find_scripts(tmp_path, "target", {".py"})

    assert set(filename_matches) == {named_match}
    assert set(partial_path_matches) == {partial_match}


def test_search_for_files_of_interest_skips_init_and_virtualenv(tmp_path: Path) -> None:
    python_file = tmp_path.joinpath("app.py")
    python_file.write_text("", encoding="utf-8")
    shell_file = tmp_path.joinpath("run.sh")
    shell_file.write_text("", encoding="utf-8")
    tmp_path.joinpath("__init__.py").write_text("", encoding="utf-8")
    venv_dir = tmp_path.joinpath(".venv")
    venv_dir.mkdir()
    venv_dir.joinpath("skip.py").write_text("", encoding="utf-8")

    result = path_helper.search_for_files_of_interest(tmp_path, suffixes={".py", ".sh"})

    assert set(result) == {python_file, shell_file}


def test_get_choice_file_uses_matcher_for_missing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = tmp_path.joinpath("found.py")
    expected.write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_match_file_name(sub_string: str, search_root: Path, suffixes: set[str]) -> Path:
        captured["sub_string"] = sub_string
        captured["search_root"] = search_root
        captured["suffixes"] = suffixes
        return expected

    monkeypatch.setattr(path_helper, "match_file_name", fake_match_file_name)

    result = path_helper.get_choice_file(
        path="missing.py",
        suffixes={".py"},
        search_root=tmp_path,
    )

    assert result == expected
    assert captured == {
        "sub_string": "missing.py",
        "search_root": tmp_path.absolute(),
        "suffixes": {".py"},
    }
