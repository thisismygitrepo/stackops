import subprocess
from typing import cast

import pytest

from stackops.jobs.installer.python_scripts import cloudflare_warp_cli
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import InstallerData


@pytest.mark.parametrize(
    ("distribution", "expected_repository", "expected_install_command", "forbidden_tokens"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="debian"),
            "/etc/apt/sources.list.d/cloudflare-client.list",
            "sudo apt-get install -y cloudflare-warp",
            ("dnf",),
            id="apt",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="fedora"),
            "/etc/yum.repos.d/cloudflare-warp.repo",
            "sudo dnf install -y cloudflare-warp",
            ("apt", "nala", "dpkg"),
            id="dnf",
        ),
    ],
)
def test_builds_native_repository_script(
    distribution: LinuxDistribution, expected_repository: str, expected_install_command: str, forbidden_tokens: tuple[str, ...]
) -> None:
    script = cloudflare_warp_cli._build_linux_install_script(distribution)

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert expected_repository in script
    assert expected_install_command in script
    assert "https://pkg.cloudflareclient.com/pubkey.gpg" in script
    assert "warp-cli registration new" in script
    for forbidden_token in forbidden_tokens:
        assert forbidden_token not in script.lower()


def test_main_detects_distribution_once_before_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    distribution = LinuxDistribution(distribution_id="fedora")
    detection_count = 0
    executed_scripts: list[str] = []

    def fake_detect_distribution() -> LinuxDistribution:
        nonlocal detection_count
        detection_count += 1
        return distribution

    def fake_run(command: list[str], text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert command[:2] == ["bash", "-c"]
        assert text is True
        assert check is True
        executed_scripts.append(command[2])
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cloudflare_warp_cli.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cloudflare_warp_cli, "detect_current_linux_distribution", fake_detect_distribution)
    monkeypatch.setattr(cloudflare_warp_cli.subprocess, "run", fake_run)

    cloudflare_warp_cli.main(installer_data=cast(InstallerData, {}), version=None, update=False)

    assert detection_count == 1
    assert len(executed_scripts) == 1
    assert "/etc/yum.repos.d/cloudflare-warp.repo" in executed_scripts[0]


@pytest.mark.parametrize("distribution_id", ["rhel", "centos"])
def test_enterprise_linux_requires_explicit_epel_setup(distribution_id: str) -> None:
    with pytest.raises(NotImplementedError, match="version-specific EPEL"):
        cloudflare_warp_cli._build_linux_install_script(LinuxDistribution(distribution_id=distribution_id))


def test_arch_linux_is_rejected_without_an_official_cloudflare_repository() -> None:
    with pytest.raises(NotImplementedError, match="does not support Linux distribution 'arch'"):
        cloudflare_warp_cli._build_linux_install_script(LinuxDistribution(distribution_id="arch"))
