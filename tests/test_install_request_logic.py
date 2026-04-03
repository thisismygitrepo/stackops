import pytest

from machineconfig.utils.installer_utils.install_request_logic import (
    InstallTarget,
    build_install_target,
    resolve_installer_value,
    should_skip_install,
    validate_install_request,
)
from machineconfig.utils.schemas.installer.installer_types import InstallRequest


def test_build_install_target_classifies_github_release() -> None:
    install_target = build_install_target(
        repo_url="https://github.com/sharkdp/fd",
        installer_value="fd-v{version}-x86_64-unknown-linux-musl.tar.gz",
    )

    assert install_target == InstallTarget(
        installer_kind="github_release",
        installer_value="fd-v{version}-x86_64-unknown-linux-musl.tar.gz",
    )


def test_validate_install_request_accepts_github_release_flags() -> None:
    install_target = InstallTarget(installer_kind="github_release", installer_value="fd-v{version}.tar.gz")

    validate_install_request(
        install_target=install_target,
        install_request=InstallRequest(version="v1.0.0", update=True),
    )


def test_validate_install_request_rejects_non_winget_package_manager_flags() -> None:
    install_target = InstallTarget(installer_kind="package_manager", installer_value="brew install git")

    with pytest.raises(NotImplementedError, match="--update/-u"):
        validate_install_request(
            install_target=install_target,
            install_request=InstallRequest(version=None, update=True),
        )


def test_resolve_installer_value_updates_winget_command() -> None:
    install_target = InstallTarget(
        installer_kind="package_manager",
        installer_value='winget install --no-upgrade --name "Git" --Id "Git.Git" --source winget',
    )

    command = resolve_installer_value(
        install_target=install_target,
        install_request=InstallRequest(version="2.50.0", update=True),
    )

    assert "--no-upgrade" not in command
    assert '--version 2.50.0' in command


def test_validate_install_request_rejects_version_for_direct_binary_url() -> None:
    install_target = InstallTarget(
        installer_kind="binary_url",
        installer_value="https://example.com/tool",
    )

    with pytest.raises(NotImplementedError, match="--version/-v"):
        validate_install_request(
            install_target=install_target,
            install_request=InstallRequest(version="1.2.3", update=False),
        )


def test_should_skip_install_only_when_request_is_plain_install() -> None:
    assert should_skip_install(
        exe_name="fd",
        install_request=InstallRequest(version=None, update=False),
        tool_exists=lambda _name: True,
    )
    assert not should_skip_install(
        exe_name="fd",
        install_request=InstallRequest(version=None, update=True),
        tool_exists=lambda _name: True,
    )
    assert not should_skip_install(
        exe_name="fd",
        install_request=InstallRequest(version="v1.0.0", update=False),
        tool_exists=lambda _name: True,
    )
