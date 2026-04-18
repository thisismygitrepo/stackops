from collections.abc import Callable
from pathlib import Path
import shutil
import subprocess
from typing import cast
import zipfile

import pytest
import typer

import stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile as cli_config_dotfile_module
import stackops.scripts.python.helpers.helpers_utils.download as download_module
import stackops.utils.io as io_module
import stackops.utils.links as links_module


type FormatSelfManagedMapperPath = Callable[[Path], str]

format_self_managed_mapper_path = cast(
    FormatSelfManagedMapperPath,
    getattr(cli_config_dotfile_module, "_format_self_managed_mapper_path"),
)


def test_format_self_managed_mapper_path_uses_config_root_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_root = tmp_path / "config-root"
    target_path = config_root / "dotfiles" / "mapper" / "bashrc"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("bash", encoding="utf-8")

    monkeypatch.setattr(cli_config_dotfile_module, "CONFIG_ROOT", str(config_root))

    assert format_self_managed_mapper_path(target_path) == "CONFIG_ROOT/dotfiles/mapper/bashrc"


def test_backup_path_round_trip_for_non_shared_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    original_path = home_path / "configs" / "nvim" / "init.lua"
    destination_root = tmp_path / "backup-root"

    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setattr(
        cli_config_dotfile_module,
        "BACKUP_ROOT_PRIVATE",
        tmp_path / "private-root",
    )
    monkeypatch.setattr(
        cli_config_dotfile_module,
        "BACKUP_ROOT_PUBLIC",
        tmp_path / "public-root",
    )

    backup_path = cli_config_dotfile_module.get_backup_path(
        orig_path=original_path,
        sensitivity="private",
        destination=str(destination_root),
        shared=False,
    )

    assert backup_path == destination_root / "init.lua"
    assert cli_config_dotfile_module.get_original_path_from_backup_path(
        backup_path=backup_path,
        sensitivity="private",
        destination=str(destination_root),
        shared=False,
    ) == home_path / "init.lua"


def test_register_dotfile_uses_copy_map_without_recording(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    original_path = home_path / ".config" / "app.toml"
    original_path.parent.mkdir(parents=True)
    original_path.write_text("content", encoding="utf-8")
    private_root = tmp_path / "private-root"
    copy_calls: list[tuple[object, object, object]] = []

    def fake_copy_map(
        config_file_default_path: object,
        config_file_self_managed_path: object,
        on_conflict: object,
    ) -> None:
        copy_calls.append(
            (
                config_file_default_path,
                config_file_self_managed_path,
                on_conflict,
            )
        )

    def fail_record_mapping(
        orig_path: Path,
        new_path: Path,
        method: str,
        section: str,
        os_filter: str,
    ) -> None:
        _ = orig_path, new_path, method, section, os_filter
        raise AssertionError("record_mapping should not run when record=False")

    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setattr(cli_config_dotfile_module, "BACKUP_ROOT_PRIVATE", private_root)
    monkeypatch.setattr(links_module, "copy_map", fake_copy_map)
    monkeypatch.setattr(cli_config_dotfile_module, "record_mapping", fail_record_mapping)

    cli_config_dotfile_module.register_dotfile(
        file=str(original_path),
        method="copy",
        on_conflict="throw-error",
        sensitivity="private",
        destination=None,
        section="default",
        os_filter="linux",
        shared=False,
        record=False,
    )

    assert len(copy_calls) == 1
    copied_default, copied_target, _copied_on_conflict = copy_calls[0]
    assert str(copied_default).endswith(".config/app.toml")
    assert str(copied_target).endswith("private-root/.config/app.toml")


def test_edit_dotfile_creates_user_mapper_and_runs_editor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_mapper_path = tmp_path / "mapper.yaml"
    editor_calls: list[list[str]] = []

    def fake_write_dotfiles_mapper(
        path: Path,
        mapper: dict[str, object],
        header: str,
    ) -> None:
        _ = mapper
        path.write_text(header, encoding="utf-8")

    def fake_run(
        args: list[str],
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        editor_calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(cli_config_dotfile_module, "USER_MAPPER_PATH", user_mapper_path)
    monkeypatch.setattr(
        cli_config_dotfile_module,
        "write_dotfiles_mapper",
        fake_write_dotfiles_mapper,
    )
    monkeypatch.setattr(shutil, "which", lambda editor: f"/bin/{editor}")
    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_config_dotfile_module.edit_dotfile(editor="hx", repo="user")

    assert user_mapper_path.exists()
    assert editor_calls == [["/bin/hx", str(user_mapper_path)]]


def test_import_dotfiles_downloads_decrypts_and_extracts_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    encrypted_path = tmp_path / "dotfiles.zip.gpg"
    encrypted_path.write_text("encrypted", encoding="utf-8")
    decrypted_zip_path = tmp_path / "dotfiles.zip"
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text("payload", encoding="utf-8")

    with zipfile.ZipFile(decrypted_zip_path, "w") as archive:
        archive.write(payload_path, arcname="payload.txt")

    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setattr(
        download_module,
        "download",
        lambda url, decompress, output_dir: encrypted_path,
    )
    monkeypatch.setattr(
        io_module,
        "decrypt_file_symmetric",
        lambda file_path, pwd: decrypted_zip_path,
    )

    cli_config_dotfile_module.import_dotfiles(
        url="http://example.test/dotfiles.zip.gpg",
        pwd="secret",
        use_ssh=False,
    )

    assert (home_path / "dotfiles" / "payload.txt").read_text(encoding="utf-8") == "payload"
    assert not decrypted_zip_path.exists()


def test_register_dotfile_exits_when_neither_path_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setattr(
        cli_config_dotfile_module,
        "BACKUP_ROOT_PRIVATE",
        tmp_path / "private-root",
    )

    with pytest.raises(typer.Exit) as exit_info:
        cli_config_dotfile_module.register_dotfile(
            file=str(home_path / "missing.txt"),
            method="copy",
            on_conflict="throw-error",
            sensitivity="private",
            destination=None,
            section="default",
            os_filter="linux",
            shared=False,
            record=False,
        )

    assert exit_info.value.exit_code == 1
