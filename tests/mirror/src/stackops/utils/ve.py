from __future__ import annotations

from pathlib import Path

import pytest

from stackops.utils import ve as ve_module


def test_read_default_cloud_config_returns_fresh_defaults() -> None:
    default_cloud_config = ve_module.read_default_cloud_config()
    another_default_cloud_config = ve_module.read_default_cloud_config()

    assert default_cloud_config == {
        "cloud": "mycloud101",
        "root": "myhome",
        "rel2home": False,
        "pwd": None,
        "key": None,
        "encrypt": False,
        "os_specific": False,
        "zip": False,
        "share": False,
        "overwrite": False,
    }

    default_cloud_config["cloud"] = "mutated"

    assert another_default_cloud_config["cloud"] == "mycloud101"


def test_get_ve_path_and_ipython_profile_reads_specs_from_nearest_config(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    nested_dir = project_dir / "pkg" / "module"
    nested_dir.mkdir(parents=True)

    (project_dir / ve_module.FILE_NAME).write_text(
        """
specs:
  ve_path: /tmp/project-venv
  ipy_profile: profile-main
""".strip(),
        encoding="utf-8",
    )

    ve_path, ipy_profile = ve_module.get_ve_path_and_ipython_profile(nested_dir)

    assert ve_path == "/tmp/project-venv"
    assert ipy_profile == "profile-main"


def test_get_ve_path_and_ipython_profile_merges_missing_specs_from_parents(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    package_dir = project_dir / "pkg"
    nested_dir = package_dir / "module"
    nested_dir.mkdir(parents=True)

    (project_dir / ve_module.FILE_NAME).write_text(
        """
specs:
  ipy_profile: profile-parent
""".strip(),
        encoding="utf-8",
    )
    (package_dir / ve_module.FILE_NAME).write_text(
        """
specs:
  ve_path: /tmp/pkg-venv
""".strip(),
        encoding="utf-8",
    )

    ve_path, ipy_profile = ve_module.get_ve_path_and_ipython_profile(nested_dir)

    assert ve_path == "/tmp/pkg-venv"
    assert ipy_profile == "profile-parent"


def test_get_ve_path_and_ipython_profile_uses_dotvenv_fallback(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    nested_dir = project_dir / "pkg" / "module"
    nested_dir.mkdir(parents=True)
    (project_dir / ".venv").mkdir()

    ve_path, ipy_profile = ve_module.get_ve_path_and_ipython_profile(nested_dir)

    assert ve_path == str((project_dir / ".venv").resolve())
    assert ipy_profile is None


def test_get_ve_path_and_ipython_profile_returns_none_when_no_sources_exist(tmp_path: Path) -> None:
    nested_dir = tmp_path / "project" / "pkg" / "module"
    nested_dir.mkdir(parents=True)

    ve_path, ipy_profile = ve_module.get_ve_path_and_ipython_profile(nested_dir)

    assert ve_path is None
    assert ipy_profile is None


@pytest.mark.parametrize(("platform_name"), [("Linux"), ("Darwin")])
def test_get_ve_activate_line_for_posix_platforms(monkeypatch: pytest.MonkeyPatch, platform_name: str) -> None:
    monkeypatch.setattr("platform.system", lambda: platform_name)

    activate_line = ve_module.get_ve_activate_line("/tmp/venv")

    assert activate_line == ". /tmp/venv/bin/activate"


def test_get_ve_activate_line_for_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    ve_root = home_dir / "venvs" / "proj"
    ve_root.mkdir(parents=True)

    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    activate_line = ve_module.get_ve_activate_line(str(ve_root))

    assert activate_line == ". $HOME/venvs/proj/Scripts/activate.ps1"


def test_get_ve_activate_line_rejects_unknown_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Platform Plan9 not supported"):
        ve_module.get_ve_activate_line("/tmp/venv")
