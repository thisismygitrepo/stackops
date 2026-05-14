import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_config_mount
from stackops.scripts.python.helpers.helpers_devops.mount_helpers import devices
from stackops.scripts.python.helpers.helpers_utils import machine_utils_app


def test_list_devices_raises_on_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(devices.platform, "system", lambda: "Plan9")

    with pytest.raises(RuntimeError, match="Unsupported platform: Plan9"):
        devices.list_devices()


def test_machine_list_devices_reports_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_config_mount, "list_devices_internal", lambda: (_ for _ in ()).throw(RuntimeError("Unsupported platform: Plan9")))

    result = CliRunner().invoke(machine_utils_app.get_app(), ["list-devices"])

    assert result.exit_code == 1
    assert "Device listing failed: Unsupported platform: Plan9" in result.stdout
