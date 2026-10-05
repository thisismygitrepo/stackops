from pathlib import Path
from typing import Literal

import pytest

from stackops.profile import create_shell_profile
from stackops.scripts.python.helpers.helpers_devops import devops_status_checks


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path.joinpath("home")
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    monkeypatch.setattr(devops_status_checks, "CONFIG_ROOT", home.joinpath(".config", "stackops"))


@pytest.fixture
def shell_paths(monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    profile_path = Path.home().joinpath(".bashrc")
    init_script = devops_status_checks.CONFIG_ROOT.joinpath("settings", "shells", "bash", "init.sh")
    init_script.parent.mkdir(parents=True)
    monkeypatch.setattr(create_shell_profile, "get_shell_profile_path", lambda: profile_path)
    monkeypatch.setattr(devops_status_checks.platform, "system", lambda: "Linux")
    return profile_path, init_script


@pytest.mark.parametrize(
    "system_name,shell_name,extension,command",
    [("Linux", "bash", "sh", "source"), ("Darwin", "zsh", "sh", "source"), ("Windows", "pwsh", "ps1", ".")],
)
def test_shell_status_matches_platform_installer(
    monkeypatch: pytest.MonkeyPatch, system_name: str, shell_name: str, extension: str, command: str
) -> None:
    profile_path = Path.home().joinpath("profile")
    init_script = devops_status_checks.CONFIG_ROOT.joinpath("settings", "shells", shell_name, f"""init.{extension}""")
    init_script.parent.mkdir(parents=True)
    init_script.write_text("shell init", encoding="utf-8")
    profile_path.write_text(f"""{command} $HOME/.config/stackops/settings/shells/{shell_name}/init.{extension}""", encoding="utf-8")
    monkeypatch.setattr(create_shell_profile, "get_shell_profile_path", lambda: profile_path)
    monkeypatch.setattr(devops_status_checks.platform, "system", lambda: system_name)

    status = devops_status_checks.check_shell_profile_status()

    assert status["configured"]
    assert status["source_line_present"]
    assert status["init_script_exists"]
    assert status["init_script_path"] == str(init_script)


@pytest.mark.parametrize("init_kind", ["missing", "directory", "broken_symlink"])
def test_shell_source_requires_a_real_init_file(shell_paths: tuple[Path, Path], init_kind: Literal["missing", "directory", "broken_symlink"]) -> None:
    profile_path, init_script = shell_paths
    profile_path.write_text("source $HOME/.config/stackops/settings/shells/bash/init.sh", encoding="utf-8")
    if init_kind == "directory":
        init_script.mkdir()
    elif init_kind == "broken_symlink":
        init_script.symlink_to(init_script.parent.joinpath("missing.sh"))

    status = devops_status_checks.check_shell_profile_status()

    assert not status["configured"]
    assert not status["init_script_exists"]


@pytest.mark.parametrize(
    "source_line",
    [
        "# source $HOME/.config/stackops/settings/shells/bash/init.sh",
        "echo source $HOME/.config/stackops/settings/shells/bash/init.sh",
        "source $HOME/.config/stackops/settings/shells/bash/init.sh.bak",
        "source $HOME/.config/stackops/profile/init.sh",
    ],
)
def test_shell_status_ignores_inactive_and_unrelated_source_lines(shell_paths: tuple[Path, Path], source_line: str) -> None:
    profile_path, init_script = shell_paths
    init_script.write_text("shell init", encoding="utf-8")
    profile_path.write_text(source_line, encoding="utf-8")

    status = devops_status_checks.check_shell_profile_status()

    assert not status["configured"]
    assert not status["source_line_present"]


@pytest.mark.parametrize("profile_kind", ["missing", "directory"])
def test_shell_status_requires_a_profile_file(shell_paths: tuple[Path, Path], profile_kind: Literal["missing", "directory"]) -> None:
    profile_path, init_script = shell_paths
    init_script.write_text("shell init", encoding="utf-8")
    if profile_kind == "directory":
        profile_path.mkdir()

    status = devops_status_checks.check_shell_profile_status()

    assert not status["exists"]
    assert not status["configured"]


def test_shell_read_failure_propagates(shell_paths: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    profile_path, _init_script = shell_paths
    profile_path.touch()

    def reject_read(_path: Path, encoding: str) -> str:
        raise PermissionError(encoding)

    monkeypatch.setattr(Path, "read_text", reject_read)

    with pytest.raises(PermissionError):
        devops_status_checks.check_shell_profile_status()


@pytest.mark.parametrize("ssh_kind", ["missing", "file", "directory"])
def test_ssh_status_returns_complete_shape_without_keys(ssh_kind: Literal["missing", "file", "directory"]) -> None:
    ssh_dir = Path.home().joinpath(".ssh")
    if ssh_kind == "file":
        ssh_dir.touch()
    elif ssh_kind == "directory":
        ssh_dir.mkdir()

    status = devops_status_checks.check_ssh_status()

    assert status == {
        "ssh_dir_path": str(ssh_dir),
        "ssh_dir_exists": ssh_kind == "directory",
        "keys": [],
        "config_exists": False,
        "authorized_keys_exists": False,
        "known_hosts_exists": False,
    }


def test_ssh_status_checks_files_and_does_not_treat_certificates_as_key_pairs() -> None:
    ssh_dir = Path.home().joinpath(".ssh")
    ssh_dir.mkdir()
    for filename in ("id_z.pub", "id_a.pub", "id_a", "id_a-cert.pub", "config", "known_hosts"):
        ssh_dir.joinpath(filename).touch()
    for directory_name in ("id_z", "directory.pub", "authorized_keys"):
        ssh_dir.joinpath(directory_name).mkdir()
    ssh_dir.joinpath("broken.pub").symlink_to(ssh_dir.joinpath("missing.pub"))

    status = devops_status_checks.check_ssh_status()

    assert [key["name"] for key in status["keys"]] == ["id_a", "id_z"]
    assert status["keys"][0]["private_exists"]
    assert not status["keys"][1]["private_exists"]
    assert status["keys"][0]["public_path"] == str(ssh_dir.joinpath("id_a.pub"))
    assert status["keys"][0]["private_path"] == str(ssh_dir.joinpath("id_a"))
    assert status["config_exists"]
    assert status["known_hosts_exists"]
    assert not status["authorized_keys_exists"]
