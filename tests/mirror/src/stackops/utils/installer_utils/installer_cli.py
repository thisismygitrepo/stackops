import pytest
import typer

from stackops.jobs.installer import package_groups
from stackops.utils.installer_utils import installer_cli
from stackops.utils.schemas.installer.installer_types import InstallRequest


def test_main_installer_cli_installs_all_requested_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_groups: list[str] = []

    def fake_install_group(*, package_group: str, install_request: InstallRequest) -> None:
        _ = install_request
        requested_groups.append(package_group)

    monkeypatch.setattr(installer_cli, "install_group", fake_install_group)

    installer_cli.main_installer_cli(
        which=" editors, agents ",
        group=True,
        interactive=False,
        update=False,
        version=None,
    )

    assert requested_groups == ["editors", "agents"]


def test_install_group_exits_nonzero_for_unknown_group(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(package_groups, "PACKAGE_GROUP2NAMES", {"valid": ["demo"]})

    with pytest.raises(typer.Exit) as exit_info:
        installer_cli.install_group(
            package_group="missing",
            install_request=InstallRequest(version=None, update=False),
        )

    assert exit_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Unknown package group: missing" in captured.out
