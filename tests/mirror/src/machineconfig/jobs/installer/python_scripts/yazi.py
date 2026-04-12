import copy
from pathlib import Path
import pathlib
import sys
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

import machineconfig.jobs.installer.python_scripts.yazi as yazi
import machineconfig.utils.code as code_utils
import machineconfig.utils.installer_utils.installer_cli as installer_cli
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


@pytest.mark.parametrize(("platform_name", "config_parts"), [("Linux", (".config", "yazi")), ("Windows", ("AppData", "Roaming", "yazi", "config"))])
def test_main_installs_dependencies_and_clones_into_platform_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform_name: str, config_parts: tuple[str, ...]
) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_dir = home_dir.joinpath(*config_parts)
    plugins_dir = config_dir / "plugins"
    flavors_dir = config_dir / "flavors"
    plugins_dir.mkdir(parents=True)
    flavors_dir.mkdir(parents=True)
    stale_plugin_file = plugins_dir / "stale.txt"
    stale_flavor_file = flavors_dir / "stale.txt"
    stale_plugin_file.write_text("old", encoding="utf-8")
    stale_flavor_file.write_text("old", encoding="utf-8")

    installer_app_names: list[str] = []
    install_versions: list[str | None] = []
    dependency_calls: list[tuple[str, str | None, bool]] = []
    clone_calls: list[tuple[str, Path]] = []
    shell_scripts: list[tuple[str, bool, bool]] = []

    class FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            installer_app_names.append(installer_data["appName"])

        def install(self, version: str | None) -> None:
            install_versions.append(version)

    def fake_path_home(cls: type[pathlib.Path]) -> Path:
        _ = cls
        return home_dir

    def fake_install_if_missing(which: str, binary_name: str | None, verbose: bool) -> None:
        dependency_calls.append((which, binary_name, verbose))

    def fake_clone_from(url: str, destination: Path) -> None:
        clone_calls.append((url, destination))

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> None:
        shell_scripts.append((script, display_script, clean_env))

    git_module = ModuleType("git")
    git_module.Repo = SimpleNamespace(clone_from=fake_clone_from)  # type: ignore[attr-defined]

    monkeypatch.setattr(yazi, "installer_standard", copy.deepcopy(yazi.installer_standard))
    monkeypatch.setattr(yazi, "Installer", FakeInstaller)
    monkeypatch.setattr(yazi.platform, "system", lambda: platform_name)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(fake_path_home))
    monkeypatch.setattr(installer_cli, "install_if_missing", fake_install_if_missing)
    monkeypatch.setattr(code_utils, "run_shell_script", fake_run_shell_script)
    monkeypatch.setitem(sys.modules, "git", git_module)

    yazi.main(installer_data=_installer_data(), version="25.1.0", update=False)

    assert installer_app_names == ["yazi", "ya"]
    assert install_versions == ["25.1.0", "25.1.0"]
    assert dependency_calls == [
        ("glow", None, True),
        ("duckdb", None, True),
        ("poppler", "pdftotext", True),
        ("viu", None, True),
        ("jq", None, True),
        ("resvg", None, True),
        ("git", None, True),
        ("7zip", "7z", True),
        ("file", None, True),
    ]
    assert clone_calls == [("https://github.com/yazi-rs/plugins", plugins_dir), ("https://github.com/yazi-rs/flavors", flavors_dir)]
    assert shell_scripts == [
        (
            """
ya pkg add 'ndtoan96/ouch'  # make ouch default previewer in yazi for compressed files
ya pkg add 'AnirudhG07/rich-preview'  # rich-cli based previewer for yazi
ya pkg add 'stelcodes/bunny'
ya pkg add 'Tyarel8/goto-drives'
ya pkg add 'uhs-robert/sshfs'
ya pkg add 'boydaihungst/file-extra-metadata'
ya pkg add 'wylie102/duckdb'
ya pkg install
""",
            True,
            False,
        )
    ]
    assert not stale_plugin_file.exists()
    assert not stale_flavor_file.exists()
