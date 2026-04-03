# pyright: reportArgumentType=false

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import bz2
import gzip
import lzma
import tarfile
import zipfile

import pytest

from machineconfig.utils import path_extended as legacy
from machineconfig.utils import path_extended_functional as functional
from machineconfig.utils.path_extended import PathExtended
from tests.path_extended_functional_support import assert_matching_outcomes, capture_call, normalize_text, snapshot_tree


class FixedReprDatetime(datetime):
    @classmethod
    def fromtimestamp(cls, timestamp: float, tz: object | None = None) -> FixedReprDatetime:
        _ = timestamp, tz
        return cls(2024, 1, 2, 3, 4, 5)


def _freeze_repr_datetime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(legacy, "datetime", FixedReprDatetime)
    monkeypatch.setattr(functional, "datetime", FixedReprDatetime)


def _mirror_roots(tmp_path: Path, name: str) -> tuple[Path, Path]:
    original_root = tmp_path / name / "original"
    functional_root = tmp_path / name / "functional"
    original_root.mkdir(parents=True)
    functional_root.mkdir(parents=True)
    return original_root, functional_root


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _zip_members(path: Path) -> tuple[tuple[str, bytes], ...]:
    with zipfile.ZipFile(path, "r") as archive:
        return tuple((name, archive.read(name)) for name in sorted(archive.namelist()))


def test_delete_matches_for_existing_and_missing_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)
    original_root, functional_root = _mirror_roots(tmp_path, "delete")
    _write_text(original_root / "keep.txt", "alpha")
    _write_text(functional_root / "keep.txt", "alpha")

    original = capture_call(lambda: PathExtended(original_root / "keep.txt").delete(sure=True))
    functional_result = capture_call(lambda: functional.delete(functional_root / "keep.txt", sure=True))
    assert_matching_outcomes(original, functional_result, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root) == snapshot_tree(functional_root)

    missing_original = capture_call(lambda: PathExtended(original_root / "missing.txt").delete(sure=True))
    missing_functional = capture_call(lambda: functional.delete(functional_root / "missing.txt", sure=True))
    assert_matching_outcomes(missing_original, missing_functional, original_root=original_root, functional_root=functional_root)


def test_move_matches_for_file_and_directory_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)

    file_original_root, file_functional_root = _mirror_roots(tmp_path, "move-file")
    _write_text(file_original_root / "src.txt", "payload")
    _write_text(file_functional_root / "src.txt", "payload")
    original = capture_call(lambda: PathExtended(file_original_root / "src.txt").move(folder=file_original_root / "dest", name="moved.txt"))
    functional_result = capture_call(lambda: functional.move(file_functional_root / "src.txt", folder=file_functional_root / "dest", name="moved.txt"))
    assert_matching_outcomes(original, functional_result, original_root=file_original_root, functional_root=file_functional_root)
    assert snapshot_tree(file_original_root) == snapshot_tree(file_functional_root)

    dir_original_root, dir_functional_root = _mirror_roots(tmp_path, "move-dir-content")
    _write_text(dir_original_root / "source" / "one.txt", "1")
    _write_text(dir_original_root / "source" / "two.txt", "2")
    _write_text(dir_functional_root / "source" / "one.txt", "1")
    _write_text(dir_functional_root / "source" / "two.txt", "2")
    original_dir = capture_call(lambda: PathExtended(dir_original_root / "source").move(folder=dir_original_root / "target" / "copied", content=True))
    functional_dir = capture_call(lambda: functional.move(dir_functional_root / "source", folder=dir_functional_root / "target" / "copied", content=True))
    assert_matching_outcomes(original_dir, functional_dir, original_root=dir_original_root, functional_root=dir_functional_root)
    assert snapshot_tree(dir_original_root) == snapshot_tree(dir_functional_root)


def test_copy_matches_for_files_and_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)

    file_original_root, file_functional_root = _mirror_roots(tmp_path, "copy-file")
    _write_text(file_original_root / "src.txt", "payload")
    _write_text(file_functional_root / "src.txt", "payload")
    original = capture_call(lambda: PathExtended(file_original_root / "src.txt").copy(folder=file_original_root / "dest", name="copied.txt"))
    functional_result = capture_call(lambda: functional.copy(file_functional_root / "src.txt", folder=file_functional_root / "dest", name="copied.txt"))
    assert_matching_outcomes(original, functional_result, original_root=file_original_root, functional_root=file_functional_root)
    assert snapshot_tree(file_original_root) == snapshot_tree(file_functional_root)

    dir_original_root, dir_functional_root = _mirror_roots(tmp_path, "copy-dir")
    _write_text(dir_original_root / "folder" / "one.txt", "1")
    _write_text(dir_original_root / "folder" / "two.txt", "2")
    _write_text(dir_functional_root / "folder" / "one.txt", "1")
    _write_text(dir_functional_root / "folder" / "two.txt", "2")
    original_dir = capture_call(lambda: PathExtended(dir_original_root / "folder").copy(folder=dir_original_root / "target", content=True))
    functional_dir = capture_call(lambda: functional.copy(dir_functional_root / "folder", folder=dir_functional_root / "target", content=True))
    assert_matching_outcomes(original_dir, functional_dir, original_root=dir_original_root, functional_root=dir_functional_root)
    assert snapshot_tree(dir_original_root) == snapshot_tree(dir_functional_root)


def test_append_and_with_name_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)

    append_original_root, append_functional_root = _mirror_roots(tmp_path, "append")
    _write_text(append_original_root / "report.txt", "payload")
    _write_text(append_functional_root / "report.txt", "payload")
    original_append = capture_call(lambda: PathExtended(append_original_root / "report.txt").append("_new", inplace=True))
    functional_append = capture_call(lambda: functional.append(append_functional_root / "report.txt", name="_new", inplace=True))
    assert_matching_outcomes(original_append, functional_append, original_root=append_original_root, functional_root=append_functional_root)
    assert snapshot_tree(append_original_root) == snapshot_tree(append_functional_root)

    with_name_original_root, with_name_functional_root = _mirror_roots(tmp_path, "with-name")
    _write_text(with_name_original_root / "report.txt", "payload")
    _write_text(with_name_original_root / "occupied.txt", "occupied")
    _write_text(with_name_functional_root / "report.txt", "payload")
    _write_text(with_name_functional_root / "occupied.txt", "occupied")
    original_with_name = capture_call(lambda: PathExtended(with_name_original_root / "report.txt").with_name("occupied.txt", inplace=True, strict=False))
    functional_with_name = capture_call(lambda: functional.with_name(with_name_functional_root / "report.txt", "occupied.txt", inplace=True, strict=False))
    assert_matching_outcomes(original_with_name, functional_with_name, original_root=with_name_original_root, functional_root=with_name_functional_root)
    assert snapshot_tree(with_name_original_root) == snapshot_tree(with_name_functional_root)


def test_symlink_to_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)
    original_root, functional_root = _mirror_roots(tmp_path, "symlink")
    _write_text(original_root / "target.txt", "payload")
    _write_text(functional_root / "target.txt", "payload")

    original = capture_call(lambda: PathExtended(original_root / "links" / "item.txt").symlink_to(original_root / "target.txt"))
    functional_result = capture_call(lambda: functional.symlink_to(functional_root / "links" / "item.txt", functional_root / "target.txt"))
    assert_matching_outcomes(original, functional_result, original_root=original_root, functional_root=functional_root)
    original_snapshot = tuple(
        (entry.rel_path, entry.kind, normalize_text(entry.payload, original_root) if isinstance(entry.payload, str) else entry.payload)
        for entry in snapshot_tree(original_root)
    )
    functional_snapshot = tuple(
        (entry.rel_path, entry.kind, normalize_text(entry.payload, functional_root) if isinstance(entry.payload, str) else entry.payload)
        for entry in snapshot_tree(functional_root)
    )
    assert original_snapshot == functional_snapshot


def test_zip_and_unzip_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)
    original_root, functional_root = _mirror_roots(tmp_path, "zip")
    _write_text(original_root / "folder" / "one.txt", "1")
    _write_text(original_root / "folder" / "two.txt", "2")
    _write_text(functional_root / "folder" / "one.txt", "1")
    _write_text(functional_root / "folder" / "two.txt", "2")

    original_zip = capture_call(lambda: PathExtended(original_root / "folder").zip(path=original_root / "archives" / "bundle"))
    functional_zip = capture_call(lambda: functional.zip(functional_root / "folder", path=functional_root / "archives" / "bundle"))
    assert_matching_outcomes(original_zip, functional_zip, original_root=original_root, functional_root=functional_root)
    assert _zip_members(original_root / "archives" / "bundle.zip") == _zip_members(functional_root / "archives" / "bundle.zip")

    original_zip_path = capture_call(lambda: functional.zip_path(functional_root / "folder", target_path=functional_root / "archives" / "bundle-2"))
    assert (functional_root / "archives" / "bundle-2.zip").exists()
    assert original_zip_path.exception_type is None

    original_unzip = capture_call(lambda: PathExtended(original_root / "archives" / "bundle.zip").unzip(folder=original_root / "unzipped", overwrite=True))
    functional_unzip = capture_call(lambda: functional.unzip(functional_root / "archives" / "bundle.zip", folder=functional_root / "unzipped", overwrite=True))
    assert_matching_outcomes(original_unzip, functional_unzip, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root / "unzipped") == snapshot_tree(functional_root / "unzipped")


def test_stream_extractors_and_decompress_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)
    original_root, functional_root = _mirror_roots(tmp_path, "stream")
    payload = b"stream-data"
    tar_member_name = "payload.txt"

    original_tar = original_root / "archive.tar"
    functional_tar = functional_root / "archive.tar"
    for tar_path in (original_tar, functional_tar):
        with tarfile.open(tar_path, "w") as tar_handle:
            source = tar_path.parent / tar_member_name
            source.write_bytes(payload)
            tar_handle.add(source, arcname=tar_member_name)
            source.unlink()

    (original_root / "archive.gz").write_bytes(gzip.compress(payload))
    (functional_root / "archive.gz").write_bytes(gzip.compress(payload))
    (original_root / "archive.xz").write_bytes(lzma.compress(payload))
    (functional_root / "archive.xz").write_bytes(lzma.compress(payload))
    (original_root / "archive.tbz").write_bytes(bz2.compress(payload))
    (functional_root / "archive.tbz").write_bytes(bz2.compress(payload))

    original_untar = capture_call(lambda: PathExtended(original_tar).untar(folder=original_root / "untarred"))
    functional_untar = capture_call(lambda: functional.untar(functional_tar, folder=functional_root / "untarred"))
    assert_matching_outcomes(original_untar, functional_untar, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root / "untarred") == snapshot_tree(functional_root / "untarred")

    original_ungz = capture_call(lambda: PathExtended(original_root / "archive.gz").ungz(folder=original_root / "gz-out"))
    functional_ungz = capture_call(lambda: functional.ungz(functional_root / "archive.gz", folder=functional_root / "gz-out"))
    assert_matching_outcomes(original_ungz, functional_ungz, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root / "gz-out") == snapshot_tree(functional_root / "gz-out")

    original_unxz = capture_call(lambda: PathExtended(original_root / "archive.xz").unxz(folder=original_root / "xz-out"))
    functional_unxz = capture_call(lambda: functional.unxz(functional_root / "archive.xz", folder=functional_root / "xz-out"))
    assert_matching_outcomes(original_unxz, functional_unxz, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root / "xz-out") == snapshot_tree(functional_root / "xz-out")

    original_unbz = capture_call(lambda: PathExtended(original_root / "archive.tbz").unbz(folder=original_root / "bz-out"))
    functional_unbz = capture_call(lambda: functional.unbz(functional_root / "archive.tbz", folder=functional_root / "bz-out"))
    assert_matching_outcomes(original_unbz, functional_unbz, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root / "bz-out") == snapshot_tree(functional_root / "bz-out")


def test_decompress_dispatch_matches_for_tar_gz_and_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)
    monkeypatch.setattr(legacy, "randstr", lambda noun=False: "fixed")  # noqa: ARG005
    monkeypatch.setattr(functional, "randstr", lambda noun=False: "fixed")  # noqa: ARG005
    original_root, functional_root = _mirror_roots(tmp_path, "decompress")
    _write_text(original_root / "folder" / "payload.txt", "hello")
    _write_text(functional_root / "folder" / "payload.txt", "hello")

    for root in (original_root, functional_root):
        with tarfile.open(root / "folder.tar", "w") as tar_handle:
            tar_handle.add(root / "folder", arcname="folder")
        (root / "folder.tar.gz").write_bytes(gzip.compress((root / "folder.tar").read_bytes()))
        (root / "folder.tar.xz").write_bytes(lzma.compress((root / "folder.tar").read_bytes()))
        (root / "folder.tar.bz2").write_bytes(bz2.compress((root / "folder.tar").read_bytes()))
        with zipfile.ZipFile(root / "folder.zip", "w") as archive:
            archive.write(root / "folder" / "payload.txt", arcname="folder/payload.txt")

    for suffix, out_name in (
        ("folder.tar.gz", "from-targz"),
        ("folder.tar.xz", "from-tarxz"),
        ("folder.tar.bz2", "from-tarbz"),
        ("folder.zip", "from-zip"),
    ):
        original = capture_call(lambda suffix=suffix, out_name=out_name: PathExtended(original_root / suffix).decompress(folder=original_root / out_name))
        functional_result = capture_call(lambda suffix=suffix, out_name=out_name: functional.decompress(functional_root / suffix, folder=functional_root / out_name))
        assert_matching_outcomes(original, functional_result, original_root=original_root, functional_root=functional_root)
        assert snapshot_tree(original_root / out_name) == snapshot_tree(functional_root / out_name)


def test_encrypt_decrypt_and_combo_helpers_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_repr_datetime(monkeypatch)

    def fake_encrypt(*, msg: bytes, key: bytes | None = None, pwd: str | None = None) -> bytes:
        _ = key, pwd
        return b"enc:" + msg

    def fake_decrypt(*, token: bytes, key: bytes | None = None, pwd: str | None = None) -> bytes:
        _ = key, pwd
        assert token.startswith(b"enc:")
        return token.removeprefix(b"enc:")

    monkeypatch.setattr(legacy, "encrypt", fake_encrypt)
    monkeypatch.setattr(legacy, "decrypt", fake_decrypt)
    monkeypatch.setattr(functional, "io_encrypt", fake_encrypt)
    monkeypatch.setattr(functional, "io_decrypt", fake_decrypt)

    original_root, functional_root = _mirror_roots(tmp_path, "crypto")
    _write_text(original_root / "payload.txt", "secret")
    _write_text(functional_root / "payload.txt", "secret")

    original_encrypt = capture_call(lambda: PathExtended(original_root / "payload.txt").encrypt(pwd="pw"))
    functional_encrypt = capture_call(lambda: functional.encrypt(functional_root / "payload.txt", pwd="pw"))
    assert_matching_outcomes(original_encrypt, functional_encrypt, original_root=original_root, functional_root=functional_root)
    assert (original_root / "payload.txt.enc").read_bytes() == (functional_root / "payload.txt.enc").read_bytes()

    original_decrypt = capture_call(lambda: PathExtended(original_root / "payload.txt.enc").decrypt(pwd="pw"))
    functional_decrypt = capture_call(lambda: functional.decrypt(functional_root / "payload.txt.enc", pwd="pw"))
    assert_matching_outcomes(original_decrypt, functional_decrypt, original_root=original_root, functional_root=functional_root)
    assert snapshot_tree(original_root) == snapshot_tree(functional_root)

    combo_original_root, combo_functional_root = _mirror_roots(tmp_path, "crypto-combo")
    _write_text(combo_original_root / "folder" / "payload.txt", "secret")
    _write_text(combo_functional_root / "folder" / "payload.txt", "secret")
    original_combo = capture_call(lambda: PathExtended(combo_original_root / "folder").zip_n_encrypt(pwd="pw"))
    functional_combo = capture_call(lambda: functional.zip_n_encrypt(combo_functional_root / "folder", pwd="pw"))
    assert_matching_outcomes(original_combo, functional_combo, original_root=combo_original_root, functional_root=combo_functional_root)

    original_roundtrip = capture_call(lambda: PathExtended(combo_original_root / "folder.zip.enc").decrypt_n_unzip(pwd="pw"))
    functional_roundtrip = capture_call(lambda: functional.decrypt_n_unzip(combo_functional_root / "folder.zip.enc", pwd="pw"))
    assert_matching_outcomes(original_roundtrip, functional_roundtrip, original_root=combo_original_root, functional_root=combo_functional_root)
    assert snapshot_tree(combo_original_root / "folder") == snapshot_tree(combo_functional_root / "folder")
