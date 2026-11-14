import pytest

from stackops.utils.installer_utils import install_request_logic, installer_runner
from stackops.utils.installer_utils.installer_bulk_plan import holds_system_installer_lock
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import OPERATING_SYSTEMS


@pytest.mark.parametrize(
    ("operating_system", "locking_apps", "parallel_apps"),
    (
        ("linux", {"yazi", "nerdfont"}, {"jq", "bat", "tokei", "agent-git", "tuios"}),
        ("windows", {"tokei", "nano", "gh", "yazi", "nerdfont"}, {"jq", "bat", "agent-git", "tuios"}),
    ),
)
def test_termabc_system_installers_and_scripts_are_serialized(
    operating_system: OPERATING_SYSTEMS, locking_apps: set[str], parallel_apps: set[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def detect_ubuntu() -> LinuxDistribution:
        return LinuxDistribution(distribution_id="ubuntu")

    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", detect_ubuntu)
    lock_by_app: dict[str, bool] = {}
    for installer in installer_runner.get_installers(os=operating_system, arch="amd64", which_cats=["termabc"]):
        installer_value = install_request_logic.resolve_installer_pattern(installer_data=installer, operating_system=operating_system, architecture="amd64")
        assert installer_value is not None
        install_target = install_request_logic.build_install_target(repo_url=installer["repoURL"], installer_value=installer_value)
        lock_by_app[installer["appName"]] = holds_system_installer_lock(install_target=install_target)

    assert {app_name for app_name, locked in lock_by_app.items() if locked} == locking_apps
    assert all(not lock_by_app[app_name] for app_name in parallel_apps)


@pytest.mark.parametrize(
    ("repo_url", "installer_value", "expected"),
    (
        ("CMD", "sudo apt-get install -y tmux", True),
        ("CMD", "winget install --id GNU.Nano", True),
        ("CMD", "yazi.py", True),
        ("CMD", "network.sh", True),
        ("https://github.com/cli/cli", "gh_{version}_windows_amd64.msi", True),
        ("https://github.com/owner/tool", "tool_{version}_amd64.deb", True),
        ("https://github.com/owner/tool", "tool-{version}.pkg.tar.zst", True),
        ("https://github.com/Einsia/agent-git", "bun install -g @einsia/agent-git", False),
        ("CMD", "cargo install tokei", False),
        ("https://github.com/BurntSushi/ripgrep", "ripgrep-{version}-x86_64-unknown-linux-musl.tar.gz", False),
    ),
)
def test_holds_system_installer_lock(repo_url: str, installer_value: str, expected: bool) -> None:
    install_target = install_request_logic.build_install_target(repo_url=repo_url, installer_value=installer_value)

    assert holds_system_installer_lock(install_target=install_target) is expected
