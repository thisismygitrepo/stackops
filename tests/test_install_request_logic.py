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

    resolution = validate_install_request(
        install_target=install_target,
        install_request=InstallRequest(version="v1.0.0", update=True),
    )

    assert resolution.install_request == InstallRequest(version="v1.0.0", update=True)
    assert resolution.warnings == ()


def test_validate_install_request_ignores_unsupported_package_manager_flags() -> None:
    install_target = InstallTarget(installer_kind="package_manager", installer_value="brew install git")

    resolution = validate_install_request(
        install_target=install_target,
        install_request=InstallRequest(version=None, update=True),
    )

    assert resolution.install_request == InstallRequest(version=None, update=False)
    assert resolution.warnings == (
        "Ignoring unsupported --update/-u for package_manager installers and continuing with the supported install flow.",
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


def test_validate_install_request_ignores_unsupported_version_for_direct_binary_url() -> None:
    install_target = InstallTarget(
        installer_kind="binary_url",
        installer_value="https://example.com/tool",
    )

    resolution = validate_install_request(
        install_target=install_target,
        install_request=InstallRequest(version="1.2.3", update=False),
    )

    assert resolution.install_request == InstallRequest(version=None, update=False)
    assert resolution.warnings == (
        "Ignoring unsupported --version/-v for binary_url installers and continuing with the supported install flow.",
    )


def test_should_skip_install_when_unsupported_flags_are_ignored() -> None:
    install_target = InstallTarget(installer_kind="package_manager", installer_value="brew install git")
    resolution = validate_install_request(
        install_target=install_target,
        install_request=InstallRequest(version="1.2.3", update=True),
    )

    assert should_skip_install(
        exe_name="git",
        install_request=resolution.install_request,
        tool_exists=lambda _name: True,
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
