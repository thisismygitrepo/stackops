

import sys
from types import ModuleType

import pytest

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_devops.mount_helpers import selection as module_under_test


def make_entry(key: str, *, label: str | None) -> DeviceEntry:
    return DeviceEntry(
        platform_name="Linux",
        key=key,
        device_path=f"/dev/{key}",
        device_type="part",
        label=label,
        mount_point=None,
        fs_type="ext4",
        size="10G",
        extra=None,
        disk_number=None,
        partition_number=None,
        drive_letter=None,
    )


def install_options_module(monkeypatch: pytest.MonkeyPatch, chooser: object) -> None:
    stub = ModuleType("stackops.utils.options")
    setattr(stub, "choose_from_options", chooser)
    monkeypatch.setitem(sys.modules, "stackops.utils.options", stub)


def test_pick_device_returns_selected_entry_and_formats_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [make_entry("sda1", label="Root"), make_entry("sdb1", label="Data")]
    captured_options: list[list[str]] = []
    captured_headers: list[str] = []

    def fake_choose_from_options(*, options: list[str], msg: str, multi: bool, header: str, tv: bool) -> str | None:
        assert msg == "Select a device"
        assert multi is False
        assert tv is True
        captured_options.append(options)
        captured_headers.append(header)
        return options[1]

    install_options_module(monkeypatch, fake_choose_from_options)

    selected = module_under_test.pick_device(entries=entries, header="Pick one")

    assert selected == entries[1]
    assert captured_headers == ["Pick one"]
    assert captured_options == [["00 sda1 | /dev/sda1 | ext4 | 10G | - | Root | -", "01 sdb1 | /dev/sdb1 | ext4 | 10G | - | Data | -"]]


@pytest.mark.parametrize(("choice", "expected_message"), [(None, "Device selection cancelled"), ("missing", "Selection not found")])
def test_pick_device_raises_for_cancelled_or_unknown_selection(monkeypatch: pytest.MonkeyPatch, choice: str | None, expected_message: str) -> None:
    def fake_choose_from_options(*, options: list[str], msg: str, multi: bool, header: str, tv: bool) -> str | None:
        _ = options
        _ = msg
        _ = multi
        _ = header
        _ = tv
        return choice

    install_options_module(monkeypatch, fake_choose_from_options)

    with pytest.raises(RuntimeError, match=expected_message):
        module_under_test.pick_device(entries=[make_entry("sda1", label="Root")], header="Pick one")


def test_resolve_device_returns_unique_exact_match() -> None:
    entries = [make_entry("sda1", label="Root"), make_entry("sdb1", label="Data")]

    selected = module_under_test.resolve_device(entries=entries, query="data")

    assert selected == entries[1]


def test_resolve_device_uses_picker_for_ambiguous_and_missing_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [make_entry("sda1", label="Data"), make_entry("sdb1", label="data"), make_entry("sdc1", label="Archive")]
    picker_calls: list[tuple[list[DeviceEntry], str]] = []

    def fake_pick_device(candidate_entries: list[DeviceEntry], header: str) -> DeviceEntry:
        picker_calls.append((candidate_entries, header))
        return candidate_entries[0]

    monkeypatch.setattr(module_under_test, "pick_device", fake_pick_device)

    first = module_under_test.resolve_device(entries=entries, query="data")
    second = module_under_test.resolve_device(entries=entries, query="missing")

    assert first == entries[0]
    assert second == entries[0]
    assert picker_calls == [([entries[0], entries[1]], "Multiple matches"), (entries, "Available devices")]
