

import gzip
from pathlib import Path

import stackops.utils.path_compression as path_compression


def test_split_embedded_archive_path_separates_archive_and_member(
    tmp_path: Path,
) -> None:
    source = tmp_path.joinpath("bundle.zip", "nested", "file.txt")

    archive_path, member = path_compression._split_embedded_archive_path(source)

    assert archive_path == tmp_path.joinpath("bundle.zip").resolve()
    assert member == Path("nested/file.txt")


def test_zip_path_and_unzip_path_round_trip_file(tmp_path: Path) -> None:
    source = tmp_path.joinpath("notes.txt")
    source.write_text("hello world", encoding="utf-8")

    archive_path = path_compression.zip_path(
        source,
        path=None,
        folder=tmp_path.joinpath("archives"),
        name="backup",
        arcname=None,
        inplace=False,
        verbose=False,
        content=False,
        orig=False,
        mode="w",
    )
    extracted_root = path_compression.unzip_path(
        archive_path,
        folder=tmp_path.joinpath("unzipped"),
        path=None,
        name=None,
        verbose=False,
        content=False,
        inplace=False,
        overwrite=False,
        orig=False,
        pwd=None,
        tmp=False,
        pattern=None,
        merge=False,
    )

    assert archive_path == tmp_path.joinpath("archives", "backup.zip").resolve()
    assert extracted_root == tmp_path.joinpath("unzipped", "backup").resolve()
    assert extracted_root.joinpath("notes.txt").read_text(encoding="utf-8") == "hello world"


def test_decompress_path_handles_gzip_files(tmp_path: Path) -> None:
    source = tmp_path.joinpath("payload.txt.gz")
    source.write_bytes(gzip.compress(b"payload"))

    result = path_compression.decompress_path(
        source,
        folder=tmp_path.joinpath("out"),
        name="payload.txt",
        path=None,
        inplace=False,
        orig=False,
        verbose=False,
    )

    assert result == tmp_path.joinpath("out", "payload.txt").resolve()
    assert result.read_bytes() == b"payload"
