from pathlib import Path
import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_utils import path_helper
from stackops.scripts.python.helpers.helpers_utils.path_helper import match_file_name, search_for_files_of_interest


def test_search_for_files_of_interest_accepts_wildcard_suffix(tmp_path: Path) -> None:
    python_file = tmp_path.joinpath("example.py")
    data_file = tmp_path.joinpath("example.csv")
    python_file.write_text("", encoding="utf-8")
    data_file.write_text("", encoding="utf-8")

    files = search_for_files_of_interest(path_obj=tmp_path, suffixes={".*"})

    assert set(files) == {python_file, data_file}


def test_match_file_name_strips_fzf_selected_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    selected_relative_path = Path("nested/example.py")

    def fake_find_scripts(root: Path, name_substring: str, suffixes: set[str]) -> tuple[list[Path], list[Path]]:
        return [], []

    def fake_run(_cmd: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["fzf"], returncode=0, stdout=f"{selected_relative_path.as_posix()}\n")

    monkeypatch.setattr(path_helper, "find_scripts", fake_find_scripts)
    monkeypatch.setattr(path_helper.subprocess, "run", fake_run)

    choice_file = match_file_name(sub_string="example", search_root=tmp_path, suffixes={".py"})

    assert choice_file == tmp_path.joinpath(selected_relative_path)
    assert "\n" not in choice_file.as_posix()
