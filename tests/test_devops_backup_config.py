from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from machineconfig.scripts.python.helpers.helpers_devops import backup_config, cli_backup_retrieve


def test_read_backup_config_reads_yaml_groups(tmp_path: Path) -> None:
    backup_path = tmp_path.joinpath("mapper_data.yaml")
    backup_path.write_text(
        """history:
  shell:
    path_local: "~/.bash_history"
    path_cloud: "^"
    encrypt: true
    zip: false
    rel2home: true
    os:
      - linux
      - darwin
""",
        encoding="utf-8",
    )

    with patch.object(backup_config, "LIBRARY_BACKUP_PATH", backup_path):
        config = backup_config.read_backup_config(repo="library")

    assert config == {
        "history": {
            "shell": {
                "path_local": "~/.bash_history",
                "path_cloud": "^",
                "encrypt": True,
                "zip": False,
                "rel2home": True,
                "os": {"linux", "darwin"},
            }
        }
    }


def test_read_backup_config_rejects_scalar_os_field(tmp_path: Path) -> None:
    backup_path = tmp_path.joinpath("mapper_data.yaml")
    backup_path.write_text(
        """history:
  shell:
    path_local: "~/.bash_history"
    path_cloud: "^"
    encrypt: true
    zip: false
    rel2home: true
    os: linux
""",
        encoding="utf-8",
    )

    with patch.object(backup_config, "LIBRARY_BACKUP_PATH", backup_path):
        with pytest.raises(ValueError, match="must define 'os' as a YAML list"):
            backup_config.read_backup_config(repo="library")


def test_register_backup_entry_writes_yaml_document(tmp_path: Path) -> None:
    local_path = tmp_path.joinpath("payload.txt")
    local_path.write_text("payload", encoding="utf-8")
    backup_path = tmp_path.joinpath("mapper_data.yaml")

    with patch.object(cli_backup_retrieve, "USER_BACKUP_PATH", backup_path):
        written_path, entry_name, replaced = cli_backup_retrieve.register_backup_entry(
            path_local=local_path.as_posix(),
            group="history",
            entry_name="session-db",
            path_cloud=None,
            zip_=True,
            encrypt=False,
            rel2home=False,
            os="linux,darwin",
        )

    raw_document = yaml.safe_load(backup_path.read_text(encoding="utf-8"))

    assert written_path == backup_path
    assert entry_name == "session_db"
    assert replaced is False
    assert raw_document == {
        "history": {
            "session_db": {
                "path_local": local_path.as_posix(),
                "path_cloud": cli_backup_retrieve.ES,
                "encrypt": False,
                "zip": True,
                "rel2home": False,
                "os": ["linux", "darwin"],
            }
        }
    }
