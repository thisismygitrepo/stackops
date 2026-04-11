from pathlib import Path
from types import ModuleType
import sys

import pytest

import machineconfig.utils.path_extended as path_extended_module
from machineconfig.scripts.python.helpers.helpers_cloud import helpers2
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.ve import read_default_cloud_config


def test_to_cloud_uses_symmetric_gpg_helper_when_password_is_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = PathExtended(tmp_path.joinpath("plain.txt"))
    source.write_text("payload", encoding="utf-8")
    encrypted_path = tmp_path.joinpath("plain.txt.gpg")
    encrypted_path.write_text("encrypted", encoding="utf-8")
    helper_calls: list[tuple[Path, str]] = []
    upload_calls: list[tuple[str, str]] = []

    def fake_copyto(*, in_path: str, out_path: str) -> None:
        upload_calls.append((in_path, out_path))

    fake_rclone_module = ModuleType("rclone_python")
    fake_rclone_module.rclone = ModuleType("rclone")  # type: ignore[attr-defined]
    fake_rclone_module.rclone.copyto = fake_copyto  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rclone_python", fake_rclone_module)

    def fake_encrypt_file_symmetric(file_path: Path, pwd: str) -> Path:
        helper_calls.append((Path(file_path), pwd))
        return encrypted_path

    monkeypatch.setattr(path_extended_module, "encrypt_file_symmetric", fake_encrypt_file_symmetric)
    monkeypatch.setattr(path_extended_module, "encrypt_file_asymmetric", lambda file_path: pytest.fail("encrypt_file_asymmetric should not be used"))

    source.to_cloud(cloud="demo", encrypt=True, pwd="hunter2", rel2home=False, os_specific=False, strict=False, verbose=False)

    assert helper_calls == [(source, "hunter2")]
    assert upload_calls == [(encrypted_path.as_posix(), upload_calls[0][1])]
    assert upload_calls[0][1].startswith("demo:")
    assert upload_calls[0][1].endswith("plain.txt.gpg")


def test_to_cloud_uses_asymmetric_gpg_helper_without_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = PathExtended(tmp_path.joinpath("plain.txt"))
    source.write_text("payload", encoding="utf-8")
    encrypted_path = tmp_path.joinpath("plain.txt.gpg")
    encrypted_path.write_text("encrypted", encoding="utf-8")
    helper_calls: list[Path] = []
    upload_calls: list[tuple[str, str]] = []

    def fake_copyto(*, in_path: str, out_path: str) -> None:
        upload_calls.append((in_path, out_path))

    fake_rclone_module = ModuleType("rclone_python")
    fake_rclone_module.rclone = ModuleType("rclone")  # type: ignore[attr-defined]
    fake_rclone_module.rclone.copyto = fake_copyto  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rclone_python", fake_rclone_module)

    def fake_encrypt_file_asymmetric(file_path: Path) -> Path:
        helper_calls.append(Path(file_path))
        return encrypted_path

    monkeypatch.setattr(path_extended_module, "encrypt_file_asymmetric", fake_encrypt_file_asymmetric)
    monkeypatch.setattr(path_extended_module, "encrypt_file_symmetric", lambda file_path, pwd: pytest.fail("encrypt_file_symmetric should not be used"))

    source.to_cloud(cloud="demo", encrypt=True, pwd=None, rel2home=False, os_specific=False, strict=False, verbose=False)

    assert helper_calls == [source]
    assert upload_calls == [(encrypted_path.as_posix(), upload_calls[0][1])]
    assert upload_calls[0][1].startswith("demo:")
    assert upload_calls[0][1].endswith("plain.txt.gpg")


def test_from_cloud_uses_symmetric_gpg_helper_when_password_is_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = PathExtended(tmp_path.joinpath("plain.txt"))
    encrypted_path = tmp_path.joinpath("plain.txt.gpg")
    encrypted_path.write_text("encrypted", encoding="utf-8")
    helper_calls: list[tuple[Path, str]] = []
    download_calls: list[tuple[str, str]] = []

    def fake_copyto(*, in_path: str, out_path: str) -> None:
        download_calls.append((in_path, out_path))

    fake_rclone_module = ModuleType("rclone_python")
    fake_rclone_module.rclone = ModuleType("rclone")  # type: ignore[attr-defined]
    fake_rclone_module.rclone.copyto = fake_copyto  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rclone_python", fake_rclone_module)

    def fake_decrypt_file_symmetric(file_path: Path, pwd: str) -> Path:
        helper_calls.append((Path(file_path), pwd))
        return destination

    monkeypatch.setattr(path_extended_module, "decrypt_file_symmetric", fake_decrypt_file_symmetric)
    monkeypatch.setattr(path_extended_module, "decrypt_file_asymmetric", lambda file_path: pytest.fail("decrypt_file_asymmetric should not be used"))

    result = destination.from_cloud(cloud="demo", decrypt=True, pwd="hunter2", rel2home=False, os_specific=False, strict=False, verbose=False)

    assert helper_calls == [(encrypted_path, "hunter2")]
    assert download_calls == [(download_calls[0][0], encrypted_path.as_posix())]
    assert download_calls[0][0].startswith("demo:")
    assert download_calls[0][0].endswith("plain.txt.gpg")
    assert result == destination


def test_from_cloud_uses_asymmetric_gpg_helper_without_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = PathExtended(tmp_path.joinpath("plain.txt"))
    encrypted_path = tmp_path.joinpath("plain.txt.gpg")
    encrypted_path.write_text("encrypted", encoding="utf-8")
    helper_calls: list[Path] = []
    download_calls: list[tuple[str, str]] = []

    def fake_copyto(*, in_path: str, out_path: str) -> None:
        download_calls.append((in_path, out_path))

    fake_rclone_module = ModuleType("rclone_python")
    fake_rclone_module.rclone = ModuleType("rclone")  # type: ignore[attr-defined]
    fake_rclone_module.rclone.copyto = fake_copyto  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rclone_python", fake_rclone_module)

    def fake_decrypt_file_asymmetric(file_path: Path) -> Path:
        helper_calls.append(Path(file_path))
        return destination

    monkeypatch.setattr(path_extended_module, "decrypt_file_asymmetric", fake_decrypt_file_asymmetric)
    monkeypatch.setattr(path_extended_module, "decrypt_file_symmetric", lambda file_path, pwd: pytest.fail("decrypt_file_symmetric should not be used"))

    result = destination.from_cloud(cloud="demo", decrypt=True, pwd=None, rel2home=False, os_specific=False, strict=False, verbose=False)

    assert helper_calls == [encrypted_path]
    assert download_calls == [(download_calls[0][0], encrypted_path.as_posix())]
    assert download_calls[0][0].startswith("demo:")
    assert download_calls[0][0].endswith("plain.txt.gpg")
    assert result == destination


def test_parse_cloud_source_target_appends_gpg_suffix_to_remote_source(tmp_path: Path) -> None:
    cloud_config_explicit = read_default_cloud_config()
    cloud_config_explicit["cloud"] = "demo"
    cloud_config_explicit["encrypt"] = True
    cloud_config_explicit["zip"] = True

    cloud, source, target = helpers2.parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        cloud_config_defaults=read_default_cloud_config(),
        cloud_config_name=None,
        source="demo:archive/plain",
        target=str(tmp_path),
    )

    assert cloud == "demo"
    assert source == "demo:archive/plain.zip.gpg"
    assert target == str(tmp_path)


def test_parse_cloud_source_target_appends_gpg_suffix_to_remote_target(tmp_path: Path) -> None:
    source = tmp_path.joinpath("plain.txt")
    source.write_text("payload", encoding="utf-8")
    cloud_config_explicit = read_default_cloud_config()
    cloud_config_explicit["cloud"] = "demo"
    cloud_config_explicit["encrypt"] = True
    cloud_config_explicit["zip"] = True

    cloud, source_value, target = helpers2.parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        cloud_config_defaults=read_default_cloud_config(),
        cloud_config_name=None,
        source=str(source),
        target="demo:archive/plain",
    )

    assert cloud == "demo"
    assert source_value == str(source)
    assert target == "demo:archive/plain.zip.gpg"
