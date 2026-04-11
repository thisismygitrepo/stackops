from pathlib import Path
import zipfile

import pytest

import machineconfig.utils.io as io_module
from machineconfig.scripts.python.helpers.helpers_devops import cli_config_dotfile, cli_share_server
from machineconfig.scripts.python.helpers.helpers_network import address
from machineconfig.scripts.python.helpers.helpers_utils import download as download_module
from machineconfig.utils import accessories


def test_export_dotfiles_uses_symmetric_gpg_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_root = tmp_path.joinpath("home", "alex")
    dotfiles_dir = home_root.joinpath("dotfiles")
    dotfiles_dir.mkdir(parents=True, exist_ok=True)
    dotfiles_dir.joinpath(".bashrc").write_text("alias ll='ls -l'\n", encoding="utf-8")
    monkeypatch.setattr(cli_config_dotfile.Path, "home", lambda: home_root)
    helper_calls: list[tuple[Path, str]] = []
    share_calls: list[tuple[str, bool, int]] = []
    flashy_calls: list[tuple[str, str]] = []

    def fake_encrypt_file_symmetric(file_path: Path, pwd: str) -> Path:
        helper_calls.append((file_path, pwd))
        encrypted_path = file_path.with_name(f"{file_path.name}.gpg")
        encrypted_path.write_text("encrypted", encoding="utf-8")
        return encrypted_path

    monkeypatch.setattr(io_module, "encrypt_file_symmetric", fake_encrypt_file_symmetric)
    monkeypatch.setattr(address, "select_lan_ipv4", lambda prefer_vpn: "192.168.20.4")
    monkeypatch.setattr(accessories, "display_with_flashy_style", lambda msg, title: flashy_calls.append((msg, title)))
    monkeypatch.setattr(cli_share_server, "web_file_explorer", lambda path, no_auth, port: share_calls.append((path, no_auth, port)))

    cli_config_dotfile.export_dotfiles(pwd="hunter2", over_internet=False, over_ssh=False)

    zipfile_path = home_root.joinpath("dotfiles.zip")
    zipfile_encrypted_path = home_root.joinpath("dotfiles.zip.gpg")
    assert helper_calls == [(zipfile_path, "hunter2")]
    assert not zipfile_path.exists()
    assert zipfile_encrypted_path.exists()
    assert share_calls == [(str(zipfile_encrypted_path), True, 8888)]
    assert flashy_calls == [("On the remote machine, run the following:\nd c i -u http://192.168.20.4:8888 -p hunter2\n", "Remote Machine Instructions")]


def test_import_dotfiles_uses_symmetric_gpg_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_root = tmp_path.joinpath("home", "alex")
    home_root.mkdir(parents=True, exist_ok=True)
    encrypted_path = home_root.joinpath("dotfiles.zip.gpg")
    encrypted_path.write_text("encrypted", encoding="utf-8")
    zipfile_path = home_root.joinpath("dotfiles.zip")
    with zipfile.ZipFile(zipfile_path, "w") as archive:
        archive.writestr(".bashrc", "alias ll='ls -l'\n")
    home_root.joinpath("dotfiles").mkdir(parents=True, exist_ok=True)
    home_root.joinpath("dotfiles", "stale.txt").write_text("stale", encoding="utf-8")
    monkeypatch.setattr(cli_config_dotfile.Path, "home", lambda: home_root)
    helper_calls: list[tuple[Path, str]] = []

    monkeypatch.setattr(download_module, "download", lambda url, decompress, output_dir: encrypted_path)

    def fake_decrypt_file_symmetric(file_path: Path, pwd: str) -> Path:
        helper_calls.append((file_path, pwd))
        return zipfile_path

    monkeypatch.setattr(io_module, "decrypt_file_symmetric", fake_decrypt_file_symmetric)

    cli_config_dotfile.import_dotfiles(url="http://192.168.20.4:8888", pwd="hunter2", use_ssh=False)

    assert helper_calls == [(encrypted_path, "hunter2")]
    assert home_root.joinpath("dotfiles", ".bashrc").read_text(encoding="utf-8") == "alias ll='ls -l'\n"
    assert not home_root.joinpath("dotfiles", "stale.txt").exists()
    assert not zipfile_path.exists()
    assert encrypted_path.exists()
