from collections.abc import Sequence
from io import StringIO
from typing import cast

import pytest
from rich.console import Console

from stackops.jobs.installer.python_scripts import ytui_music
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import InstallerData


def test_linux_packages_use_apt_on_debian(monkeypatch: pytest.MonkeyPatch) -> None:
    executed_commands: list[tuple[str, ...]] = []

    def fake_run(command: Sequence[str], console: Console, description: str, *, required: bool) -> bool:
        _ = console, description, required
        executed_commands.append(tuple(command))
        return True

    monkeypatch.setattr(ytui_music, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="debian"))
    monkeypatch.setattr(ytui_music.shutil, "which", lambda _name: "/usr/bin/present")
    monkeypatch.setattr(ytui_music, "_is_root", lambda: False)
    monkeypatch.setattr(ytui_music, "_run", fake_run)

    ytui_music._install_linux_packages(console=Console(file=StringIO()))

    flattened_command = {part for command in executed_commands for part in command}
    assert "apt-get" in flattened_command
    assert {"nala", "yum", "pacman", "zypper", "apk"}.isdisjoint(flattened_command)
    assert executed_commands == [
        ("sudo", "apt-get", "update"),
        ("sudo", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", *ytui_music.DEBIAN_REQUIRED_PACKAGES),
        ("sudo", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", *ytui_music.DEBIAN_OPTIONAL_PACKAGES),
    ]


@pytest.mark.parametrize("distribution_id", ["fedora", "rhel", "centos", "rocky", "almalinux"])
def test_dnf_distributions_fail_before_running_commands(monkeypatch: pytest.MonkeyPatch, distribution_id: str) -> None:
    monkeypatch.setattr(ytui_music, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id=distribution_id))
    monkeypatch.setattr(ytui_music, "_run", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="libmpv.so.1"):
        ytui_music._install_linux_packages(console=Console(file=StringIO()))


def test_arch_fails_before_running_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ytui_music, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="arch"))
    monkeypatch.setattr(ytui_music, "_run", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match=r"Arch Linux provides libmpv[.]so[.]2"):
        ytui_music._install_linux_packages(console=Console(file=StringIO()))


def test_alpine_fails_before_running_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ytui_music, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(ytui_music, "_run", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="Alpine-compatible musl"):
        ytui_music._install_linux_packages(console=Console(file=StringIO()))


def test_alpine_main_rejects_before_downloading_release_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ytui_music, "get_os_name", lambda: "linux")
    monkeypatch.setattr(ytui_music, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(ytui_music.platform, "system", lambda: "Linux")
    monkeypatch.setattr(ytui_music, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(ytui_music, "Installer", lambda *_args, **_kwargs: pytest.fail("Release installer may not run"))

    with pytest.raises(NotImplementedError, match="Alpine-compatible musl"):
        ytui_music.main(installer_data=cast(InstallerData, {}), version=None, update=False)
