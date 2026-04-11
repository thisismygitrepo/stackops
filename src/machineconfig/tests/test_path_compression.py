from __future__ import annotations

import bz2
import gzip
import lzma
from pathlib import Path
import tarfile

import machineconfig.utils.path_compression as path_compression
from machineconfig.utils.path_extended import PathExtended


def test_zip_path_round_trip_directory(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("payload")
    source_dir.mkdir()
    source_dir.joinpath("nested").mkdir()
    source_dir.joinpath("nested", "file.txt").write_text("hello", encoding="utf-8")

    archive_path = path_compression.zip_path(
        source=source_dir,
        path=None,
        folder=tmp_path,
        name="payload_bundle",
        arcname=None,
        inplace=False,
        verbose=False,
        content=False,
        orig=False,
        mode="w",
    )

    extracted_path = path_compression.unzip_path(
        source=archive_path,
        folder=tmp_path.joinpath("extract"),
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

    assert archive_path == tmp_path.joinpath("payload_bundle.zip")
    assert extracted_path == tmp_path.joinpath("extract", "payload_bundle")
    assert extracted_path.joinpath("payload", "nested", "file.txt").read_text(encoding="utf-8") == "hello"


def test_unzip_path_content_true_returns_extract_root(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("payload")
    source_dir.mkdir()
    source_dir.joinpath("one.txt").write_text("1", encoding="utf-8")
    archive_path = path_compression.zip_path(
        source=source_dir, path=None, folder=tmp_path, name=None, arcname=None, inplace=False, verbose=False, content=False, orig=False, mode="w"
    )

    extracted_root = path_compression.unzip_path(
        source=archive_path,
        folder=tmp_path.joinpath("landing"),
        path=None,
        name=None,
        verbose=False,
        content=True,
        inplace=False,
        overwrite=False,
        orig=False,
        pwd=None,
        tmp=False,
        pattern=None,
        merge=False,
    )

    assert extracted_root == tmp_path.joinpath("landing")
    assert extracted_root.joinpath("payload", "one.txt").read_text(encoding="utf-8") == "1"


def test_untar_path_extracts_archive(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("payload")
    source_dir.mkdir()
    source_dir.joinpath("item.txt").write_text("tar", encoding="utf-8")
    archive_path = tmp_path.joinpath("payload.tar")
    with tarfile.open(archive_path, "w") as archive:
        archive.add(source_dir, arcname=source_dir.name)

    extracted_path = path_compression.untar_path(
        source=archive_path, folder=tmp_path.joinpath("extract"), name=None, path=None, inplace=False, orig=False, verbose=False
    )

    assert extracted_path == tmp_path.joinpath("extract", "payload")
    assert extracted_path.joinpath("payload", "item.txt").read_text(encoding="utf-8") == "tar"


def test_stream_decompressors_restore_original_bytes(tmp_path: Path) -> None:
    payload = b"strict-bytes"
    gzip_path = tmp_path.joinpath("item.txt.gz")
    gzip_path.write_bytes(gzip.compress(payload))
    lzma_path = tmp_path.joinpath("item.txt.xz")
    lzma_path.write_bytes(lzma.compress(payload))
    bz2_path = tmp_path.joinpath("item.txt.bz2")
    bz2_path.write_bytes(bz2.compress(payload))

    ungz_result = path_compression.ungz_path(source=gzip_path, folder=None, name=None, path=None, inplace=False, orig=False, verbose=False)
    unxz_result = path_compression.unxz_path(source=lzma_path, folder=None, name=None, path=None, inplace=False, orig=False, verbose=False)
    unbz_result = path_compression.unbz_path(source=bz2_path, folder=None, name=None, path=None, inplace=False, orig=False, verbose=False)

    assert ungz_result.read_bytes() == payload
    assert unxz_result.read_bytes() == payload
    assert unbz_result.read_bytes() == payload


def test_decompress_path_targz_round_trip(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("payload")
    source_dir.mkdir()
    source_dir.joinpath("item.txt").write_text("nested", encoding="utf-8")
    tar_path = tmp_path.joinpath("payload.tar")
    with tarfile.open(tar_path, "w") as archive:
        archive.add(source_dir, arcname=source_dir.name)
    targz_path = tmp_path.joinpath("payload.tar.gz")
    targz_path.write_bytes(gzip.compress(tar_path.read_bytes()))

    extracted_path = path_compression.decompress_path(
        source=targz_path, folder=tmp_path.joinpath("extract"), name=None, path=None, inplace=False, orig=False, verbose=False
    )

    assert extracted_path.joinpath("payload", "item.txt").read_text(encoding="utf-8") == "nested"


def test_unzip_path_tmp_matches_path_extended_return_shape(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("payload")
    source_dir.mkdir()
    source_dir.joinpath("nested").mkdir()
    source_dir.joinpath("nested", "file.txt").write_text("hello", encoding="utf-8")
    archive_path = path_compression.zip_path(
        source=source_dir,
        path=None,
        folder=tmp_path,
        name="payload_bundle",
        arcname=None,
        inplace=False,
        verbose=False,
        content=False,
        orig=False,
        mode="w",
    )

    old_result = Path(PathExtended(archive_path).unzip(verbose=False, tmp=True))
    new_result = path_compression.unzip_path(
        source=archive_path,
        folder=None,
        path=None,
        name=None,
        verbose=False,
        content=False,
        inplace=False,
        overwrite=False,
        orig=False,
        pwd=None,
        tmp=True,
        pattern=None,
        merge=False,
    )

    assert new_result.name == old_result.name
    assert new_result.exists() is old_result.exists()


def test_decompress_targz_matches_path_extended_return_name(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("payload")
    source_dir.mkdir()
    source_dir.joinpath("item.txt").write_text("nested", encoding="utf-8")
    tar_path = tmp_path.joinpath("payload.tar")
    with tarfile.open(tar_path, "w") as archive:
        archive.add(source_dir, arcname=source_dir.name)
    targz_path = tmp_path.joinpath("payload.tar.gz")
    targz_path.write_bytes(gzip.compress(tar_path.read_bytes()))

    old_result = Path(PathExtended(targz_path).decompress(folder=tmp_path.joinpath("old_extract"), verbose=False))
    new_result = path_compression.decompress_path(
        source=targz_path, folder=tmp_path.joinpath("new_extract"), name=None, path=None, inplace=False, orig=False, verbose=False
    )

    assert new_result.name.startswith("tmp_")
    assert len(new_result.name) == len(old_result.name)
    assert new_result.joinpath("payload", "item.txt").read_text(encoding="utf-8") == "nested"


def test_unbz_path_matches_path_extended_default_name(tmp_path: Path) -> None:
    payload = b"strict-bytes"
    source = tmp_path.joinpath("item.txt.bz2")
    source.write_bytes(bz2.compress(payload))

    old_result = Path(PathExtended(source).unbz(verbose=False))
    new_result = path_compression.unbz_path(source=source, folder=None, name=None, path=None, inplace=False, orig=False, verbose=False)

    assert new_result.name == old_result.name
    assert new_result.read_bytes() == payload
