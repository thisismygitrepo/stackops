# pyright: reportPrivateUsage=false
from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_cloud import cloud_copy
from machineconfig.scripts.python.helpers.helpers_cloud import helpers2 as cloud_helpers2


def test_artifact_path_appends_requested_suffixes() -> None:
    local_path = Path("/tmp/payload")

    assert cloud_copy._artifact_path(local_path=local_path, zip_requested=False, encrypt_requested=False) == local_path
    assert cloud_copy._artifact_path(local_path=local_path, zip_requested=True, encrypt_requested=False) == Path("/tmp/payload.zip")
    assert cloud_copy._artifact_path(local_path=local_path, zip_requested=False, encrypt_requested=True) == Path("/tmp/payload.gpg")
    assert cloud_copy._artifact_path(local_path=local_path, zip_requested=True, encrypt_requested=True) == Path("/tmp/payload.zip.gpg")


def test_prepare_upload_path_zips_then_encrypts_with_password(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path, object | None]] = []

    class FakePathExtended:
        def __init__(self, path: Path) -> None:
            self.path = path

        def zip(self, *, inplace: bool) -> str:
            calls.append(("zip", self.path, inplace))
            return f"{self.path}.zip"

    def fake_encrypt_file_symmetric(*, file_path: Path, pwd: str) -> Path:
        calls.append(("encrypt", file_path, pwd))
        return Path(f"{file_path}.gpg")

    monkeypatch.setattr(cloud_copy, "PathExtended", FakePathExtended)
    monkeypatch.setattr(cloud_copy, "encrypt_file_symmetric", fake_encrypt_file_symmetric)

    upload_path, temp_paths = cloud_copy._prepare_upload_path(
        local_path=tmp_path.joinpath("payload"), zip_requested=True, encrypt_requested=True, pwd="secret"
    )

    assert upload_path == tmp_path.joinpath("payload.zip.gpg")
    assert temp_paths == [tmp_path.joinpath("payload.zip"), tmp_path.joinpath("payload.zip.gpg")]
    assert calls == [("zip", tmp_path.joinpath("payload"), False), ("encrypt", tmp_path.joinpath("payload.zip"), "secret")]


def test_finalize_download_path_decrypts_then_unzips(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path, object | None]] = []

    class FakePathExtended:
        def __init__(self, path: Path) -> None:
            self.path = path

        def unzip(self, *, inplace: bool, verbose: bool, overwrite: bool, content: bool, merge: bool) -> str:
            calls.append(("unzip", self.path, (inplace, verbose, overwrite, content, merge)))
            return str(tmp_path.joinpath("payload"))

    def fake_decrypt_file_asymmetric(*, file_path: Path) -> Path:
        calls.append(("decrypt", file_path, None))
        return tmp_path.joinpath("payload.zip")

    monkeypatch.setattr(cloud_copy, "PathExtended", FakePathExtended)
    monkeypatch.setattr(cloud_copy, "decrypt_file_asymmetric", fake_decrypt_file_asymmetric)
    monkeypatch.setattr(cloud_copy, "delete_path", lambda target, *, verbose: calls.append(("delete", Path(target), verbose)))

    result = cloud_copy._finalize_download_path(
        download_path=tmp_path.joinpath("payload.zip.gpg"), zip_requested=True, encrypt_requested=True, pwd=None, overwrite=True
    )

    assert result == tmp_path.joinpath("payload")
    assert calls == [
        ("decrypt", tmp_path.joinpath("payload.zip.gpg"), None),
        ("delete", tmp_path.joinpath("payload.zip.gpg"), False),
        ("unzip", tmp_path.joinpath("payload.zip"), (True, True, True, True, False)),
    ]


def test_main_converts_google_drive_open_link_for_secure_share(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, str | None]] = []

    def fake_get_securely_shared_file(url: str | None, folder: str | None) -> None:
        calls.append((url, folder))

    monkeypatch.setattr(cloud_copy, "get_securely_shared_file", fake_get_securely_shared_file)

    cloud_copy.main(
        source="https://drive.google.com/open?id=file-123",
        target="/tmp/out",
        overwrite=False,
        share=False,
        rel2home=False,
        root="root",
        key=None,
        pwd=None,
        encrypt=False,
        zip_=False,
        os_specific=False,
        config="ss",
    )

    assert calls == [("https://drive.google.com/uc?export=download&id=file-123", "/tmp/out")]


def test_main_upload_share_writes_share_url_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_path = tmp_path.joinpath("payload.txt")
    source_path.write_text("payload", encoding="utf-8")

    def fake_parse_cloud_source_target(
        *, cloud_config_explicit: object, cloud_config_defaults: object, cloud_config_name: str | None, source: str, target: str
    ) -> tuple[str, str, str]:
        return "cloudx", source, "cloudx:/remote/payload.txt"

    def fake_prepare_upload_path(*, local_path: Path, zip_requested: bool, encrypt_requested: bool, pwd: str | None) -> tuple[Path, list[Path]]:
        return local_path, []

    def fake_to_cloud(*, local_path: Path, cloud: str, remote_path: Path, share: bool, verbose: bool, transfers: int) -> str:
        assert local_path == source_path
        assert cloud == "cloudx"
        assert remote_path == Path("/remote/payload.txt")
        assert share is True
        assert verbose is True
        assert transfers == 10
        return "https://share.example/payload"

    monkeypatch.setattr(cloud_helpers2, "parse_cloud_source_target", fake_parse_cloud_source_target)
    monkeypatch.setattr(cloud_copy, "_prepare_upload_path", fake_prepare_upload_path)
    monkeypatch.setattr(cloud_copy.rclone_wrapper, "to_cloud", fake_to_cloud)

    cloud_copy.main(
        source=str(source_path),
        target="ignored",
        overwrite=False,
        share=True,
        rel2home=False,
        root="root",
        key=None,
        pwd=None,
        encrypt=False,
        zip_=False,
        os_specific=False,
        config=None,
    )

    assert source_path.with_suffix(".share_url_cloudx").read_text(encoding="utf-8") == ("https://share.example/payload")
