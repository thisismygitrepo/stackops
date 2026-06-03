from pathlib import Path

from typer.testing import CliRunner
import yaml

from stackops.scripts.python.devops import get_app
from stackops.scripts.python.helpers.helpers_devops import backup_config, cli_backup_retrieve
import stackops.utils.code as code_utils


def test_devops_data_register_accepts_comment_only_user_mapper(monkeypatch, tmp_path: Path) -> None:
    backup_path = tmp_path / "dotfiles" / "stackops" / "mapper" / "data.yaml"
    backup_path.parent.mkdir(parents=True)
    backup_path.write_text(backup_config.DEFAULT_BACKUP_HEADER, encoding="utf-8")
    local_path = tmp_path / "README.md"
    local_path.write_text("# Test\n", encoding="utf-8")

    monkeypatch.setattr(backup_config, "USER_BACKUP_PATH", backup_path)
    monkeypatch.setattr(cli_backup_retrieve, "USER_BACKUP_PATH", backup_path)

    result = CliRunner().invoke(get_app(), ["d", "r", str(local_path)])

    assert result.exit_code == 0, result.output
    assert f"Added backup entry 'README' in {backup_path}" in result.output

    document = yaml.safe_load(backup_path.read_text(encoding="utf-8"))
    assert document == {
        "default": {
            "README": {
                "path_local": local_path.as_posix(),
                "path_cloud": "^",
                "share_url": None,
                "encrypt": True,
                "zip": True,
                "rel2home": False,
                "os": ["linux", "darwin", "windows"],
            }
        }
    }


def test_backup_config_loads_missing_share_url_as_none(tmp_path: Path) -> None:
    backup_path = tmp_path / "data.yaml"
    backup_path.write_text(
        """
default:
  README:
    path_local: /tmp/README.md
    path_cloud: "^"
    encrypt: true
    zip: true
    rel2home: false
    os:
      - linux
      - darwin
      - windows
""",
        encoding="utf-8",
    )

    config = backup_config._load_backup_config(backup_path)

    assert config is not None
    assert config["default"]["README"]["share_url"] is None


def test_data_sync_uses_cloud_from_path_cloud_without_default_cloud(monkeypatch, tmp_path: Path) -> None:
    backup_path = tmp_path / "data.yaml"
    backup_path.write_text(
        """
default:
  README:
    path_local: /tmp/README.md
    path_cloud: "entrycloud:^"
    share_url: null
    encrypt: true
    zip: true
    rel2home: false
    os:
      - linux
      - darwin
      - windows
""",
        encoding="utf-8",
    )
    scripts: list[str] = []

    monkeypatch.setattr(backup_config, "USER_BACKUP_PATH", backup_path)
    monkeypatch.setattr(cli_backup_retrieve, "read_ini", lambda _path: (_ for _ in ()).throw(FileNotFoundError))
    monkeypatch.setattr(code_utils, "run_shell_script", lambda script, **_kwargs: scripts.append(script))

    cli_backup_retrieve.main_backup_retrieve(direction="BACKUP", which="default.README", cloud=None, repo="user")

    assert scripts == ['\ncloud copy "/tmp/README.md" "entrycloud:^" -ze\n']
