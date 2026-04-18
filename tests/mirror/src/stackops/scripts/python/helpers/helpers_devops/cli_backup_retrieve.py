from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_devops.backup_config as backup_config_module
import stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve as cli_backup_retrieve_module
import stackops.utils.code as code_module


def test_register_backup_entry_writes_home_relative_entry_and_updates_existing_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    user_backup_path = tmp_path / "mapper_data.yaml"
    local_file = home_path / "docs" / "notes.txt"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("notes", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setattr(cli_backup_retrieve_module, "USER_BACKUP_PATH", user_backup_path)
    monkeypatch.setattr(backup_config_module, "USER_BACKUP_PATH", user_backup_path)

    written_path, entry_name, replaced = cli_backup_retrieve_module.register_backup_entry(
        path_local=str(local_file), group="My Group", entry_name=None, path_cloud=None, zip_=True, encrypt=False, rel2home=None, os="linux"
    )

    assert written_path == user_backup_path
    assert entry_name == "notes_linux"
    assert replaced is False
    assert backup_config_module.read_backup_config(repo="user") == {
        "My_Group": {
            "notes_linux": {
                "path_local": "~/docs/notes.txt",
                "path_cloud": cli_backup_retrieve_module.ES,
                "zip": True,
                "encrypt": False,
                "rel2home": True,
                "os": {"linux"},
            }
        }
    }

    _, updated_entry_name, updated_replaced = cli_backup_retrieve_module.register_backup_entry(
        path_local=str(local_file),
        group="My Group",
        entry_name=entry_name,
        path_cloud="backups/notes",
        zip_=False,
        encrypt=True,
        rel2home=True,
        os="linux",
    )

    assert updated_entry_name == "notes_linux"
    assert updated_replaced is True
    assert backup_config_module.read_backup_config(repo="user") == {
        "My_Group": {
            "notes_linux": {
                "path_local": "~/docs/notes.txt",
                "path_cloud": "backups/notes",
                "zip": False,
                "encrypt": True,
                "rel2home": True,
                "os": {"linux"},
            }
        }
    }


def test_register_backup_entry_rejects_rel2home_for_paths_outside_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("data", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setattr(cli_backup_retrieve_module, "USER_BACKUP_PATH", tmp_path / "mapper_data.yaml")

    with pytest.raises(ValueError, match="not under the home directory"):
        cli_backup_retrieve_module.register_backup_entry(
            path_local=str(outside_file), group="default", entry_name=None, path_cloud=None, zip_=True, encrypt=True, rel2home=True, os="linux"
        )


def test_main_backup_retrieve_generates_linux_backup_script(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_programs: list[str] = []
    config: backup_config_module.BackupConfig = {
        "dotfiles": {
            "bash": {"path_local": "~/.bashrc", "path_cloud": None, "zip": True, "encrypt": False, "rel2home": True, "os": {"linux"}},
            "zsh": {"path_local": "~/.zshrc", "path_cloud": None, "zip": True, "encrypt": False, "rel2home": True, "os": {"darwin"}},
        }
    }

    def fake_read_ini(_path: Path) -> dict[str, dict[str, str]]:
        return {"general": {"rclone_config_name": "maincloud"}}

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        _ = lexer, desc
        captured_programs.append(code)

    def fake_run_shell_script(program: str, display_script: bool, clean_env: bool) -> None:
        _ = display_script, clean_env
        captured_programs.append(program)

    monkeypatch.setattr(cli_backup_retrieve_module, "read_backup_config", lambda repo: config)
    monkeypatch.setattr(cli_backup_retrieve_module, "read_ini", fake_read_ini)
    monkeypatch.setattr(cli_backup_retrieve_module, "system", lambda: "Linux")
    monkeypatch.setattr(cli_backup_retrieve_module, "print_code", fake_print_code)
    monkeypatch.setattr(code_module, "run_shell_script", fake_run_shell_script)

    cli_backup_retrieve_module.main_backup_retrieve(direction="BACKUP", which="dotfiles.bash", cloud=None, repo="all")

    script = captured_programs[-1]
    assert 'cloud copy "~/.bashrc" "maincloud:^" -zro' in script
    assert "chmod 700 ~/.ssh/*" in script
    assert ".zshrc" not in script


def test_main_backup_retrieve_rejects_unknown_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    config: backup_config_module.BackupConfig = {
        "group": {"item": {"path_local": "~/data.txt", "path_cloud": None, "zip": False, "encrypt": False, "rel2home": True, "os": {"linux"}}}
    }

    monkeypatch.setattr(cli_backup_retrieve_module, "read_backup_config", lambda repo: config)
    monkeypatch.setattr(cli_backup_retrieve_module, "system", lambda: "Linux")

    with pytest.raises(ValueError, match="Unknown backup entries: missing"):
        cli_backup_retrieve_module.main_backup_retrieve(direction="BACKUP", which="missing", cloud="cloud", repo="user")
