import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_config_mount
from stackops.scripts.python.helpers.helpers_utils import machine_utils_app


def test_mount_allows_udisksctl_without_mount_point(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, bool, cli_config_mount.MountBackend]] = []

    def fake_mount_device(device_query: str, mount_point: str, read_only: bool, backend: cli_config_mount.MountBackend) -> None:
        calls.append((device_query, mount_point, read_only, backend))

    monkeypatch.setattr(cli_config_mount, "mount_device", fake_mount_device)

    result = CliRunner().invoke(machine_utils_app.get_app(), ["mount", "--device", "/dev/sda1", "--backend", "udisksctl"])

    assert result.exit_code == 0
    assert calls == [("/dev/sda1", "", False, "udisksctl")]


def test_mount_requires_mount_point_for_mount_backend() -> None:
    result = CliRunner().invoke(machine_utils_app.get_app(), ["mount", "--device", "/dev/sda1"])

    assert result.exit_code == 2
    assert "--mount-point is required unless --interactive is set or --backend udisksctl is used" in result.stdout
