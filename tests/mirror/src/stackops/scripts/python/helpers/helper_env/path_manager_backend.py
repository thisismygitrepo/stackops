from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helper_env import path_manager_backend


@pytest.mark.parametrize(
    ("platform_name", "path_value", "expected"), [("Windows", r"C:\One;C:\Two;;", [r"C:\One", r"C:\Two"]), ("Linux", "/one:/two::", ["/one", "/two"])]
)
def test_get_path_entries_splits_using_platform_separator(
    monkeypatch: pytest.MonkeyPatch, platform_name: str, path_value: str, expected: list[str]
) -> None:
    def fake_get_platform() -> str:
        return platform_name

    monkeypatch.setattr(path_manager_backend, "get_platform", fake_get_platform)
    monkeypatch.setenv("PATH", path_value)

    assert path_manager_backend.get_path_entries() == expected


def test_get_directory_contents_reports_missing_and_non_directory(tmp_path: Path) -> None:
    missing_directory = tmp_path.joinpath("missing")
    file_path = tmp_path.joinpath("file.txt")
    file_path.write_text("content", encoding="utf-8")

    assert path_manager_backend.get_directory_contents(missing_directory.as_posix()) == ["⚠️  Directory does not exist"]
    assert path_manager_backend.get_directory_contents(file_path.as_posix()) == ["⚠️  Not a directory"]


def test_get_directory_contents_orders_directories_before_files_and_truncates(tmp_path: Path) -> None:
    tmp_path.joinpath("z-dir").mkdir()
    tmp_path.joinpath("A-dir").mkdir()
    tmp_path.joinpath("b-file.txt").write_text("b", encoding="utf-8")
    tmp_path.joinpath("a-file.txt").write_text("a", encoding="utf-8")

    contents = path_manager_backend.get_directory_contents(tmp_path.as_posix(), max_items=2)

    assert contents == ["📁 A-dir", "📁 z-dir", "... and 2 more items"]


def test_get_directory_contents_handles_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_exists(self: Path) -> bool:
        _ = self
        return True

    def fake_is_dir(self: Path) -> bool:
        _ = self
        return True

    def fake_iterdir(self: Path) -> Iterator[Path]:
        _ = self
        raise PermissionError
        yield Path("/")

    monkeypatch.setattr(path_manager_backend.Path, "exists", fake_exists)
    monkeypatch.setattr(path_manager_backend.Path, "is_dir", fake_is_dir)
    monkeypatch.setattr(path_manager_backend.Path, "iterdir", fake_iterdir)

    assert path_manager_backend.get_directory_contents("/protected") == ["⚠️  Permission denied"]
