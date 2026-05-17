from pathlib import Path
import zipfile

import pytest
import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_dotfile
from stackops.scripts.python.helpers.helpers_devops import cli_share_server
from stackops.scripts.python.helpers.helpers_network import address
from stackops.utils import accessories
from stackops.utils import io as io_module


def test_export_dotfiles_requires_lan_ipv4(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    dotfiles_dir = tmp_path / "dotfiles"
    dotfiles_dir.mkdir()
    (dotfiles_dir / ".zshrc").write_text("export EDITOR=hx\n", encoding="utf-8")

    def fake_make_archive(
        base_name: str,
        format: str,
        root_dir: str,
        base_dir: str,
        verbose: bool,
    ) -> str:
        assert format == "zip"
        assert root_dir == str(dotfiles_dir)
        assert base_dir == "."
        assert verbose is False
        archive_path = Path(f"{base_name}.zip")
        archive_path.write_bytes(b"zip-data")
        return str(archive_path)

    def fake_encrypt_file_symmetric(file_path: Path, pwd: str) -> Path:
        assert file_path == tmp_path / "dotfiles.zip"
        assert pwd == "secret"
        encrypted_path = tmp_path / "dotfiles.zip.gpg"
        encrypted_path.write_bytes(b"encrypted-data")
        return encrypted_path

    def fail_display_with_flashy_style(*, msg: str, title: str) -> None:
        del msg, title
        raise AssertionError("display should not be reached without a LAN IPv4 address")

    def fail_web_file_explorer(*, path: str, no_auth: bool, port: int) -> None:
        del path, no_auth, port
        raise AssertionError("share server should not start without a LAN IPv4 address")

    monkeypatch.setattr(cli_config_dotfile.shutil, "make_archive", fake_make_archive)
    monkeypatch.setattr(io_module, "encrypt_file_symmetric", fake_encrypt_file_symmetric)
    monkeypatch.setattr(address, "select_lan_ipv4", lambda *, prefer_vpn: None)
    monkeypatch.setattr(accessories, "display_with_flashy_style", fail_display_with_flashy_style)
    monkeypatch.setattr(cli_share_server, "web_file_explorer", fail_web_file_explorer)

    with pytest.raises(typer.Exit) as exc_info:
        cli_config_dotfile.export_dotfiles(pwd="secret", over_internet=False, over_ssh=False)

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Could not determine local LAN IPv4 address for dotfiles export." in captured.err


def test_import_dotfiles_uses_existing_local_archive_without_downloading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    encrypted_path = tmp_path / "incoming" / "dotfiles.zip.gpg"
    encrypted_path.parent.mkdir()
    encrypted_path.write_bytes(b"encrypted-data")

    decrypted_zip_path = tmp_path / "dotfiles.zip"
    with zipfile.ZipFile(decrypted_zip_path, "w") as zip_ref:
        zip_ref.writestr(".zshrc", "export EDITOR=hx\n")

    def fail_download(*, url: str, decompress: bool, output_dir: str) -> Path | None:
        del url, decompress, output_dir
        raise AssertionError("download should not be called for an existing local archive path")

    def fake_decrypt_file_symmetric(file_path: str | Path, pwd: str) -> Path:
        assert Path(file_path) == encrypted_path
        assert pwd == "secret"
        return decrypted_zip_path

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_utils.download.download", fail_download)
    monkeypatch.setattr(io_module, "decrypt_file_symmetric", fake_decrypt_file_symmetric)

    cli_config_dotfile.import_dotfiles(url=str(encrypted_path), pwd="secret", use_ssh=False)

    assert tmp_path.joinpath("dotfiles", ".zshrc").read_text(encoding="utf-8") == "export EDITOR=hx\n"
    assert not decrypted_zip_path.exists()


def test_import_dotfiles_reports_gpg_errors_for_local_archives(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    encrypted_path = tmp_path / "incoming" / "dotfiles.zip.gpg"
    encrypted_path.parent.mkdir()
    encrypted_path.write_bytes(b"encrypted-data")

    def fail_download(*, url: str, decompress: bool, output_dir: str) -> Path | None:
        del url, decompress, output_dir
        raise AssertionError("download should not be called for an existing local archive path")

    def fail_decrypt_file_symmetric(file_path: str | Path, pwd: str) -> Path:
        assert Path(file_path) == encrypted_path
        assert pwd == "secret"
        raise io_module.GpgCommandError(
            command=["gpg", "--decrypt", str(encrypted_path)],
            returncode=2,
            stdout="",
            stderr="gpg: decryption failed: Bad session key",
            hint="The provided password was rejected by GPG. Verify --password and try again.",
        )

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_utils.download.download", fail_download)
    monkeypatch.setattr(io_module, "decrypt_file_symmetric", fail_decrypt_file_symmetric)

    with pytest.raises(typer.Exit) as exc_info:
        cli_config_dotfile.import_dotfiles(url=str(encrypted_path), pwd="secret", use_ssh=False)

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "GPG command failed." in captured.out
    assert "The provided password was rejected by GPG." in captured.out
    assert not tmp_path.joinpath("dotfiles").exists()
