from pathlib import Path

import pytest
import typer

import machineconfig.scripts.python.helpers.helpers_devops.cli_config_mount as cli_config_mount_module
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry


def _make_device(key: str, device_type: str | None, fs_type: str | None, mount_point: str | None) -> DeviceEntry:
    return DeviceEntry(
        platform_name="Linux",
        key=key,
        device_path=f"/dev/{key}",
        device_type=device_type,
        label=None,
        mount_point=mount_point,
        fs_type=fs_type,
        size="1T",
        extra=None,
        disk_number=None,
        partition_number=None,
        drive_letter=None,
    )


@pytest.mark.parametrize(("value", "expected"), [(None, "-"), ("", "-"), ("value", "value")])
def test_display_value_handles_missing_text(value: str | None, expected: str) -> None:
    assert cli_config_mount_module._display_value(value) == expected


def test_list_devices_reports_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []

    monkeypatch.setattr(cli_config_mount_module, "list_devices_internal", lambda: [])
    monkeypatch.setattr(cli_config_mount_module.typer, "echo", messages.append)

    cli_config_mount_module.list_devices()

    assert messages == ["No devices found"]


def test_mount_device_on_linux_selects_partition_and_mounts(monkeypatch: pytest.MonkeyPatch) -> None:
    disk_entry = _make_device("sda", "disk", None, None)
    partition_entry = _make_device("sda1", "part", "ext4", None)
    mount_calls: list[tuple[DeviceEntry, str, bool, str]] = []

    def fake_mount_linux(entry: DeviceEntry, mount_point: str, read_only: bool, backend: str) -> None:
        mount_calls.append((entry, mount_point, read_only, backend))

    monkeypatch.setattr(cli_config_mount_module, "list_devices_internal", lambda: [disk_entry, partition_entry])
    monkeypatch.setattr(cli_config_mount_module, "resolve_device", lambda entries, device_query: disk_entry)
    monkeypatch.setattr(cli_config_mount_module, "select_linux_partition", lambda entries, entry: partition_entry)
    monkeypatch.setattr(cli_config_mount_module, "mount_linux", fake_mount_linux)
    monkeypatch.setattr(cli_config_mount_module.platform, "system", lambda: "Linux")

    cli_config_mount_module.mount_device(device_query="sda", mount_point="/mnt/data", read_only=True, backend="mount")

    assert mount_calls == [(partition_entry, "/mnt/data", True, "mount")]


def test_mount_interactive_rejects_invalid_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _make_device("sda1", "part", "ext4", None)
    prompts = iter(["/mnt/data", "invalid-backend"])
    messages: list[str] = []

    def fake_prompt(*_args: object, **_kwargs: object) -> str:
        return next(prompts)

    def fake_confirm(*_args: object, **_kwargs: object) -> bool:
        return False

    monkeypatch.setattr(cli_config_mount_module, "list_devices_internal", lambda: [entry])
    monkeypatch.setattr(cli_config_mount_module, "pick_device", lambda entries, header: entry)
    monkeypatch.setattr(cli_config_mount_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli_config_mount_module.typer, "prompt", fake_prompt)
    monkeypatch.setattr(cli_config_mount_module.typer, "confirm", fake_confirm)
    monkeypatch.setattr(cli_config_mount_module.typer, "echo", messages.append)

    with pytest.raises(typer.Exit) as exit_info:
        cli_config_mount_module.mount_interactive()

    assert exit_info.value.exit_code == 2
    assert messages == ["Invalid backend: invalid-backend"]
