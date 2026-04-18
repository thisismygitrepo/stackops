from __future__ import annotations

from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_cloud import cloud_helpers


def test_find_cloud_config_walks_up_to_nearest_ve_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_root = tmp_path.joinpath("repo")
    nested_path = config_root.joinpath("a", "b", "c")
    nested_path.mkdir(parents=True)
    config_root.joinpath(".ve.yaml").write_text(
        """
cloud:
  cloud: repo-cloud
  root: repo-root
  rel2home: false
  pwd: null
  key: null
  encrypt: true
  os_specific: false
  zip: true
  share: false
  overwrite: true
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(cloud_helpers, "display_header", lambda title: None)
    monkeypatch.setattr(cloud_helpers, "display_success", lambda message: None)
    monkeypatch.setattr(cloud_helpers, "display_error", lambda message: None)
    monkeypatch.setattr(cloud_helpers, "pprint", lambda payload, header: None)

    config = cloud_helpers.find_cloud_config(path=nested_path)

    assert config is not None
    assert config["cloud"] == "repo-cloud"
    assert config["root"] == "repo-root"
    assert config["encrypt"] is True


def test_my_abs_prefers_existing_path_from_current_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local_file = tmp_path.joinpath("demo.txt")
    local_file.write_text("demo", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cloud_helpers, "display_warning", lambda message: None)

    resolved = cloud_helpers.my_abs(path="demo.txt")

    assert resolved == local_file


def test_get_secure_share_cloud_config_uses_env_and_default_password_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakePath:
        @staticmethod
        def home() -> Path:
            return tmp_path

    password_file = tmp_path.joinpath("dotfiles", "creds", "passwords", "quick_password")
    password_file.parent.mkdir(parents=True)
    password_file.write_text("pw-from-file\n", encoding="utf-8")

    monkeypatch.setenv("CLOUD_CONFIG_NAME", "cloud-from-env")
    monkeypatch.setattr(cloud_helpers, "Path", FakePath)
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    monkeypatch.setattr(cloud_helpers, "display_success", lambda message: None)
    monkeypatch.setattr(cloud_helpers, "pprint", lambda payload, header: None)

    config = cloud_helpers.get_secure_share_cloud_config(interactive=False, cloud=None)

    assert config == {
        "cloud": "cloud-from-env",
        "pwd": "pw-from-file",
        "encrypt": True,
        "zip": True,
        "overwrite": True,
        "share": True,
        "rel2home": True,
        "root": "myshare",
        "os_specific": False,
        "key": None,
    }
