

import pytest

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_devops.mount_helpers import devices as module_under_test


def make_entry(platform_name: str, key: str) -> DeviceEntry:
    return DeviceEntry(
        platform_name=platform_name,
        key=key,
        device_path=f"/dev/{key}",
        device_type="part",
        label=None,
        mount_point=None,
        fs_type=None,
        size=None,
        extra=None,
        disk_number=None,
        partition_number=None,
        drive_letter=None,
    )


@pytest.mark.parametrize(
    ("platform_name", "expected"),
    [("Linux", [make_entry("Linux", "linux0")]), ("Darwin", [make_entry("Darwin", "disk0s1")]), ("Windows", [make_entry("Windows", "C")])],
)
def test_list_devices_dispatches_by_platform(monkeypatch: pytest.MonkeyPatch, platform_name: str, expected: list[DeviceEntry]) -> None:
    linux_result = [make_entry("Linux", "linux0")]
    macos_result = [make_entry("Darwin", "disk0s1")]
    windows_result = [make_entry("Windows", "C")]

    monkeypatch.setattr(module_under_test.platform, "system", lambda: platform_name)
    monkeypatch.setattr(module_under_test, "list_linux_devices", lambda: linux_result)
    monkeypatch.setattr(module_under_test, "list_macos_devices", lambda: macos_result)
    monkeypatch.setattr(module_under_test, "list_windows_devices", lambda: windows_result)

    returned = module_under_test.list_devices()

    assert returned == expected


def test_list_devices_returns_empty_list_for_unknown_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module_under_test.platform, "system", lambda: "Plan9")

    returned = module_under_test.list_devices()

    assert returned == []
