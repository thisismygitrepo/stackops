from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_devops.mount_helpers import utils as module_under_test


def make_entry() -> DeviceEntry:
    return DeviceEntry(
        platform_name="Linux",
        key="sda1",
        device_path="/dev/sda1",
        device_type="part",
        label="",
        mount_point=None,
        fs_type="ext4",
        size="10G",
        extra="",
        disk_number=None,
        partition_number=None,
        drive_letter=None,
    )


def test_as_str_returns_only_non_empty_strings() -> None:
    assert module_under_test.as_str(value="data") == "data"
    assert module_under_test.as_str(value="") is None
    assert module_under_test.as_str(value=7) is None


def test_format_size_bytes_scales_values() -> None:
    assert module_under_test.format_size_bytes(size_bytes=512) == "512 B"
    assert module_under_test.format_size_bytes(size_bytes=2048) == "2.0 KB"
    assert module_under_test.format_size_bytes(size_bytes=5 * 1024 * 1024) == "5.0 MB"


def test_format_device_replaces_missing_values_with_dashes() -> None:
    formatted = module_under_test.format_device(entry=make_entry())

    assert formatted == "sda1 | /dev/sda1 | ext4 | 10G | - | - | -"
