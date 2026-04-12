from __future__ import annotations

import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

from machineconfig.scripts.python.helpers.helpers_devops import devops_status_checks as module


def install_profile_create_shell_profile_module(monkeypatch: pytest.MonkeyPatch, profile_path: Path) -> None:
    import machineconfig.profile as profile_package

    profile_module = ModuleType("machineconfig.profile.create_shell_profile")

    def fake_get_shell_profile_path() -> Path:
        return profile_path

    setattr(profile_module, "get_shell_profile_path", fake_get_shell_profile_path)
    monkeypatch.setitem(sys.modules, "machineconfig.profile.create_shell_profile", profile_module)
    monkeypatch.setattr(profile_package, "create_shell_profile", profile_module, raising=False)


def test_check_shell_profile_status_creates_missing_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import platform

    profile_path = tmp_path.joinpath("profiles/.bashrc")
    init_script_relative_path = Path("shells/init.sh")
    init_script_path = tmp_path.joinpath(init_script_relative_path)
    init_script_path.parent.mkdir(parents=True)
    init_script_path.write_text("echo init\n", encoding="utf-8")
    install_profile_create_shell_profile_module(monkeypatch, profile_path)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(module, "CONFIG_ROOT", tmp_path)
    monkeypatch.setattr(module.PathExtended, "collapseuser", lambda self: self)
    monkeypatch.setattr(module, "get_path_reference_library_relative_path", lambda *, module, path_reference: init_script_relative_path)

    result = module.check_shell_profile_status()

    assert profile_path.exists() is True
    assert result["profile_path"] == str(profile_path)
    assert result["configured"] is False
    assert result["init_script_exists"] is True


def test_check_repos_status_reports_missing_and_git_repos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    io_module = ModuleType("machineconfig.utils.io")
    git_module = ModuleType("git")
    existing_repo = tmp_path.joinpath("repo")
    missing_repo = tmp_path.joinpath("missing")
    existing_repo.mkdir()

    class FakeHead:
        is_detached = False

    class FakeBranch:
        name = "main"

    class FakeRepo:
        head = FakeHead()
        active_branch = FakeBranch()

        def __init__(self, path: str) -> None:
            assert path == str(existing_repo)

        def is_dirty(self, *, untracked_files: bool) -> bool:
            assert untracked_files is True
            return False

    def fake_read_ini(path: Path) -> dict[str, dict[str, str]]:
        assert path == module.DEFAULTS_PATH
        return {"general": {"repos": f"{existing_repo}, {missing_repo}"}}

    setattr(io_module, "read_ini", fake_read_ini)
    setattr(git_module, "Repo", FakeRepo)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.io", io_module)
    monkeypatch.setitem(sys.modules, "git", git_module)

    result = module.check_repos_status()

    assert result["configured"] is True
    assert result["count"] == 2
    assert result["repos"] == [
        {
            "path": str(existing_repo),
            "name": existing_repo.name,
            "exists": True,
            "is_repo": True,
            "clean": True,
            "branch": "main",
        },
        {
            "path": str(missing_repo),
            "name": missing_repo.name,
            "exists": False,
            "is_repo": False,
        },
    ]


def test_check_ssh_status_reports_keys_and_supporting_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ssh_dir = tmp_path.joinpath(".ssh")
    ssh_dir.mkdir()
    ssh_dir.joinpath("id_ed25519.pub").write_text("pub", encoding="utf-8")
    ssh_dir.joinpath("id_ed25519").write_text("priv", encoding="utf-8")
    ssh_dir.joinpath("config").write_text("Host *\n", encoding="utf-8")
    ssh_dir.joinpath("known_hosts").write_text("example\n", encoding="utf-8")
    monkeypatch.setattr(module.PathExtended, "home", classmethod(lambda cls: module.PathExtended(tmp_path)))

    result = module.check_ssh_status()

    assert result["ssh_dir_exists"] is True
    assert result["config_exists"] is True
    assert result["authorized_keys_exists"] is False
    assert result["known_hosts_exists"] is True
    assert result["keys"] == [
        {
            "name": "id_ed25519",
            "public_exists": True,
            "private_exists": True,
            "public_path": str(ssh_dir.joinpath("id_ed25519.pub")),
            "private_path": str(ssh_dir.joinpath("id_ed25519")),
        }
    ]


def test_config_item_is_configured_for_identical_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    default_path = tmp_path.joinpath("default.txt")
    default_path.write_text("same", encoding="utf-8")
    managed_path = tmp_path.joinpath("managed.txt")
    managed_path.write_text("same", encoding="utf-8")
    monkeypatch.setattr(module, "CONFIG_ROOT", tmp_path)

    config_item: module.ConfigStatusItem = {
        "config_file_default_path": str(default_path),
        "config_file_self_managed_path": "CONFIG_ROOT/managed.txt",
        "contents": False,
        "copy": True,
    }

    assert module._config_item_is_configured(config_item) is True


def test_check_config_files_status_aggregates_link_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    import machineconfig.profile as profile_package

    links_module = ModuleType("machineconfig.profile.create_links")
    public_item: module.ConfigStatusItem = {
        "config_file_default_path": "/tmp/public-linked",
        "config_file_self_managed_path": "CONFIG_ROOT/public-linked",
        "contents": False,
        "copy": False,
    }
    private_item: module.ConfigStatusItem = {
        "config_file_default_path": "/tmp/private-missing",
        "config_file_self_managed_path": "CONFIG_ROOT/private-missing",
        "contents": False,
        "copy": False,
    }

    def fake_read_mapper(*, repo: str) -> dict[str, dict[str, list[module.ConfigStatusItem]]]:
        assert repo == "all"
        return {
            "public": {"tool-a": [public_item]},
            "private": {"tool-b": [private_item]},
        }

    def fake_config_item_is_configured(config_item: module.ConfigStatusItem) -> bool:
        return config_item["config_file_default_path"].endswith("linked")

    setattr(links_module, "read_mapper", fake_read_mapper)
    monkeypatch.setitem(sys.modules, "machineconfig.profile.create_links", links_module)
    monkeypatch.setattr(profile_package, "create_links", links_module, raising=False)
    monkeypatch.setattr(module, "_config_item_is_configured", fake_config_item_is_configured)

    result = module.check_config_files_status()

    assert result == {
        "public_count": 1,
        "public_linked": 1,
        "private_count": 1,
        "private_linked": 0,
        "public_program_count": 1,
        "private_program_count": 1,
        "public_configs": ["tool-a"],
        "private_configs": ["tool-b"],
    }


def test_check_important_tools_uses_shutil_which(monkeypatch: pytest.MonkeyPatch) -> None:
    package_groups_module = ModuleType("machineconfig.jobs.installer.package_groups")

    def fake_which(name: str) -> str | None:
        return "/usr/bin/git" if name == "git" else None

    setattr(package_groups_module, "PACKAGE_GROUP2NAMES", {"core_tools": ("git", "fd")})
    monkeypatch.setitem(sys.modules, "machineconfig.jobs.installer.package_groups", package_groups_module)
    monkeypatch.setattr(shutil, "which", fake_which)

    assert module.check_important_tools() == {"core_tools": {"git": True, "fd": False}}


def test_check_backup_config_collects_named_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    io_module = ModuleType("machineconfig.utils.io")
    backup_module = ModuleType("machineconfig.scripts.python.helpers.helpers_devops.backup_config")
    backup_file = tmp_path.joinpath("backup.toml")
    backup_file.write_text("[x]\n", encoding="utf-8")

    def fake_read_ini(path: Path) -> dict[str, dict[str, str]]:
        assert path == module.DEFAULTS_PATH
        return {"general": {"rclone_config_name": "cloud-main"}}

    def fake_read_backup_config(*, repo: str) -> dict[str, dict[str, object]]:
        assert repo == "library"
        return {
            "docs": {"daily": object()},
            "media": {"photos": object(), "videos": object()},
        }

    setattr(io_module, "read_ini", fake_read_ini)
    setattr(backup_module, "LIBRARY_BACKUP_PATH", backup_file)
    setattr(backup_module, "read_backup_config", fake_read_backup_config)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.io", io_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_devops.backup_config", backup_module)

    result = module.check_backup_config()

    assert result["cloud_config"] == "cloud-main"
    assert result["backup_items_count"] == 3
    assert result["backup_items"] == ["docs.daily", "media.photos", "media.videos"]
