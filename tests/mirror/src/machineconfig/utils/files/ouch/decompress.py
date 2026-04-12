from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pytest

from machineconfig.utils.files.ouch.decompress import decompress_and_remove_zip


def test_decompress_and_remove_zip_extracts_archive_and_deletes_zip(tmp_path: Path) -> None:
    archive_path = tmp_path.joinpath("payload.zip")
    with ZipFile(archive_path, "w") as zip_file:
        zip_file.writestr("nested/data.txt", "hello")

    decompress_and_remove_zip(archive_path)

    assert not archive_path.exists()
    assert tmp_path.joinpath("nested", "data.txt").read_text(encoding="utf-8") == "hello"


def test_decompress_and_remove_zip_rejects_directory_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="is not a file"):
        decompress_and_remove_zip(tmp_path)


def test_decompress_and_remove_zip_raises_for_invalid_zip(tmp_path: Path) -> None:
    archive_path = tmp_path.joinpath("broken.zip")
    archive_path.write_text("not a zip archive", encoding="utf-8")

    with pytest.raises(BadZipFile, match="not a valid zip archive"):
        decompress_and_remove_zip(archive_path)

    assert archive_path.is_file()
