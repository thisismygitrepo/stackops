import platform
import subprocess
from pathlib import Path
from typing import Literal

import pytest

from stackops.profile import create_helper, create_shell_profile
from stackops.scripts.python.helpers.helpers_devops import devops_status_checks
from stackops.utils import source_of_truth


@pytest.fixture
def shell_installation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, list[Literal["settings", "scripts"]]]:
    home = tmp_path.joinpath("home")
    home.mkdir()
    config_root = home.joinpath(".config", "stackops")
    profile_path = home.joinpath(".bashrc")
    copied_assets: list[Literal["settings", "scripts"]] = []
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    monkeypatch.setattr(source_of_truth, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(devops_status_checks, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(create_shell_profile, "get_shell_profile_path", lambda: profile_path)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess(args=["cat", "/proc/version"], returncode=0, stdout="Linux")
    )

    def copy_fixture_assets(which: Literal["settings", "scripts"]) -> None:
        copied_assets.append(which)
        if which == "settings":
            init_script = config_root.joinpath("settings", "shells", "bash", "init.sh")
            init_script.parent.mkdir(parents=True, exist_ok=True)
            init_script.write_text("fixture init", encoding="utf-8")

    monkeypatch.setattr(create_helper, "copy_assets_to_machine", copy_fixture_assets)
    return profile_path, copied_assets


@pytest.mark.parametrize(
    "inactive_line",
    [
        "# source $HOME/.config/stackops/settings/shells/bash/init.sh",
        "echo source $HOME/.config/stackops/settings/shells/bash/init.sh",
        "source $HOME/.config/stackops/settings/shells/bash/init.sh.bak",
    ],
)
def test_default_shell_installer_adds_active_source_after_inactive_mentions(
    shell_installation: tuple[Path, list[Literal["settings", "scripts"]]], inactive_line: str
) -> None:
    profile_path, copied_assets = shell_installation
    profile_path.write_text(inactive_line, encoding="utf-8")

    create_shell_profile.create_default_shell_profile()

    source_line = "source $HOME/.config/stackops/settings/shells/bash/init.sh"
    profile_lines = profile_path.read_text(encoding="utf-8").splitlines()
    assert profile_lines[0] == inactive_line
    assert profile_lines.count(source_line) == 1
    assert copied_assets == ["settings", "scripts"]
    assert devops_status_checks.check_shell_profile_status()["configured"]

    create_shell_profile.create_default_shell_profile()

    assert profile_path.read_text(encoding="utf-8").splitlines().count(source_line) == 1


def test_default_shell_installer_preserves_existing_active_source(shell_installation: tuple[Path, list[Literal["settings", "scripts"]]]) -> None:
    profile_path, _copied_assets = shell_installation
    original = "  source $HOME/.config/stackops/settings/shells/bash/init.sh  "
    profile_path.write_text(original, encoding="utf-8")

    create_shell_profile.create_default_shell_profile()

    assert profile_path.read_text(encoding="utf-8") == original
    assert devops_status_checks.check_shell_profile_status()["configured"]
