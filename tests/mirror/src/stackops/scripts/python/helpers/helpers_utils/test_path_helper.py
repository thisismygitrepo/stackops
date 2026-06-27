from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.path_helper import search_for_files_of_interest


def test_search_for_files_of_interest_accepts_wildcard_suffix(tmp_path: Path) -> None:
    python_file = tmp_path.joinpath("example.py")
    data_file = tmp_path.joinpath("example.csv")
    python_file.write_text("", encoding="utf-8")
    data_file.write_text("", encoding="utf-8")

    files = search_for_files_of_interest(path_obj=tmp_path, suffixes={".*"})

    assert set(files) == {python_file, data_file}
