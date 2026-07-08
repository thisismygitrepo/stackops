import subprocess
from typing import cast

import pytest

from stackops.jobs.installer.python_scripts import docker
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxDistributionId
from stackops.utils.schemas.installer.installer_types import InstallerData


@pytest.mark.parametrize(
    ("distribution", "repository_url", "suite_expression"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="ubuntu"),
            "https://download.docker.com/linux/ubuntu",
            "${UBUNTU_CODENAME:-$VERSION_CODENAME}",
            id="ubuntu",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="debian"),
            "https://download.docker.com/linux/debian",
            "$VERSION_CODENAME",
            id="debian",
        ),
    ],
)
def test_apt_script_uses_exact_official_repository(distribution: LinuxDistribution, repository_url: str, suite_expression: str) -> None:
    script = docker._get_linux_install_script(distribution=distribution)

    assert "set -euo pipefail" in script
    assert f"URIs: {repository_url}" in script
    assert f'Suites: $(. /etc/os-release && echo "{suite_expression}")' in script
    assert "sudo apt-get update" in script
    assert "sudo apt-get install -y ca-certificates curl" in script
    assert "sudo apt-get install -y docker-ce docker-ce-cli containerd.io" in script
    assert "dnf" not in script.lower()
    assert "nala" not in script.lower()


@pytest.mark.parametrize(
    ("distribution_id", "repository_url"),
    [
        pytest.param("rhel", "https://download.docker.com/linux/rhel/docker-ce.repo", id="rhel"),
        pytest.param("centos", "https://download.docker.com/linux/centos/docker-ce.repo", id="centos"),
        pytest.param("ol", "https://download.docker.com/linux/rhel/docker-ce.repo", id="oracle-linux"),
    ],
)
def test_enterprise_linux_scripts_use_exact_compatible_repository(
    distribution_id: LinuxDistributionId,
    repository_url: str,
) -> None:
    distribution = LinuxDistribution(distribution_id=distribution_id)

    script = docker._get_linux_install_script(distribution=distribution)

    assert "sudo dnf -y install dnf-plugins-core" in script
    assert f'sudo dnf config-manager --add-repo "{repository_url}"' in script
    assert "sudo dnf install -y docker-ce docker-ce-cli containerd.io" in script
    for apt_only_token in ("apt", "nala", "dpkg", "sources.list"):
        assert apt_only_token not in script.lower()


def test_fedora_script_uses_dnf5_repository_command() -> None:
    distribution = LinuxDistribution(distribution_id="fedora")

    script = docker._get_linux_install_script(distribution=distribution)

    assert 'sudo dnf config-manager addrepo --from-repofile "https://download.docker.com/linux/fedora/docker-ce.repo"' in script
    assert "dnf-plugins-core" not in script
    assert "sudo dnf install -y docker-ce docker-ce-cli containerd.io" in script
    for apt_only_token in ("apt", "nala", "dpkg", "sources.list"):
        assert apt_only_token not in script.lower()


@pytest.mark.parametrize(
    "distribution",
    [
        LinuxDistribution(distribution_id="ubuntu"),
        LinuxDistribution(distribution_id="debian"),
        LinuxDistribution(distribution_id="rhel"),
        LinuxDistribution(distribution_id="fedora"),
        LinuxDistribution(distribution_id="centos"),
        LinuxDistribution(distribution_id="ol"),
    ],
)
def test_linux_scripts_share_strict_installation_tail(distribution: LinuxDistribution) -> None:
    script = docker._get_linux_install_script(distribution=distribution)

    assert "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin" in script
    assert "sudo systemctl enable --now docker" in script
    assert 'sudo usermod -aG docker "$(id -un)"' in script
    assert "sudo docker run hello-world" in script
    assert "||" not in script


@pytest.mark.parametrize("distribution_id", ["rocky", "almalinux", "linuxmint"])
def test_unofficial_derivatives_are_rejected(distribution_id: LinuxDistributionId) -> None:
    distribution = LinuxDistribution(distribution_id=distribution_id)

    with pytest.raises(NotImplementedError, match=distribution_id):
        docker._get_linux_install_script(distribution=distribution)


def test_main_detects_linux_distribution_before_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    distribution = LinuxDistribution(distribution_id="rhel")
    executed_scripts: list[str] = []

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        _ = code, lexer, desc

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> subprocess.CompletedProcess[bytes]:
        assert display_script is True
        assert clean_env is False
        executed_scripts.append(script)
        return subprocess.CompletedProcess(args=["bash"], returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(docker.platform, "system", lambda: "Linux")
    monkeypatch.setattr(docker, "detect_current_linux_distribution", lambda: distribution)
    monkeypatch.setattr(docker, "print_code", fake_print_code)
    monkeypatch.setattr(docker, "run_shell_script", fake_run_shell_script)

    docker.main(installer_data=cast(InstallerData, {}), version=None, update=False)

    assert len(executed_scripts) == 1
    assert "https://download.docker.com/linux/rhel/docker-ce.repo" in executed_scripts[0]
