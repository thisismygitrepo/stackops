from dataclasses import FrozenInstanceError

import pytest

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry


def make_entry() -> DeviceEntry:
    return DeviceEntry(
        platform_name="Linux",
        key="sda1",
        device_path="/dev/sda1",
        device_type="part",
        label="root",
        mount_point="/",
        fs_type="ext4",
        size="100G",
        extra="disk",
        disk_number=0,
        partition_number=1,
        drive_letter=None,
    )


def test_device_entry_compares_and_hashes_by_value() -> None:
    left = make_entry()
    right = make_entry()

    assert left == right
    assert hash(left) == hash(right)


def test_device_entry_is_frozen() -> None:
    entry = make_entry()

    with pytest.raises(FrozenInstanceError):
        setattr(entry, "key", "sdb1")
