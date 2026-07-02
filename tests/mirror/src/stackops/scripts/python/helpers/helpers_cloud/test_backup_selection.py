import pytest

from stackops.profile.dotfiles_mapper import OsName
from stackops.scripts.python.helpers.helpers_cloud.backup_config import BackupConfig, BackupItem
from stackops.scripts.python.helpers.helpers_cloud.backup_selection import (
    BackupEntryKey,
    parse_backup_entry_selectors,
    resolve_backup_entry_keys,
)


def test_resolve_backup_entry_keys_combines_specific_entries_and_whole_groups() -> None:
    config = _backup_config()

    selectors = parse_backup_entry_selectors(" alpha.two, beta ")
    selected_keys = resolve_backup_entry_keys(config=config, selectors=selectors)

    assert selected_keys == [
        BackupEntryKey(group_name="alpha", item_name="two"),
        BackupEntryKey(group_name="beta", item_name="three"),
        BackupEntryKey(group_name="beta", item_name="four"),
    ]


def test_resolve_backup_entry_keys_deduplicates_overlapping_selectors() -> None:
    config = _backup_config()

    selectors = parse_backup_entry_selectors("alpha.two,alpha,alpha.two")
    selected_keys = resolve_backup_entry_keys(config=config, selectors=selectors)

    assert selected_keys == [
        BackupEntryKey(group_name="alpha", item_name="two"),
        BackupEntryKey(group_name="alpha", item_name="one"),
    ]


@pytest.mark.parametrize("which", ["", "alpha,", ",alpha", "alpha,,beta", "all,alpha"])
def test_parse_backup_entry_selectors_rejects_invalid_values(which: str) -> None:
    with pytest.raises(ValueError, match="Invalid --which value"):
        parse_backup_entry_selectors(which)


def test_resolve_backup_entry_keys_reports_every_unknown_selector() -> None:
    config = _backup_config()
    selectors = parse_backup_entry_selectors("missing,alpha.missing,beta.three")

    with pytest.raises(ValueError, match="Unknown backup entries: missing, alpha.missing"):
        resolve_backup_entry_keys(config=config, selectors=selectors)


def test_resolve_backup_entry_keys_selects_all_entries() -> None:
    config = _backup_config()

    selectors = parse_backup_entry_selectors("all")
    selected_keys = resolve_backup_entry_keys(config=config, selectors=selectors)

    assert selected_keys == [
        BackupEntryKey(group_name="alpha", item_name="one"),
        BackupEntryKey(group_name="alpha", item_name="two"),
        BackupEntryKey(group_name="beta", item_name="three"),
        BackupEntryKey(group_name="beta", item_name="four"),
    ]


def _backup_config() -> BackupConfig:
    return {
        "alpha": {
            "one": _backup_item(path_local="~/alpha-one", os_values={"linux"}),
            "two": _backup_item(path_local="~/alpha-two", os_values={"darwin"}),
        },
        "beta": {
            "three": _backup_item(path_local="~/beta-three", os_values={"windows"}),
            "four": _backup_item(path_local="~/beta-four", os_values={"linux"}),
        },
    }


def _backup_item(*, path_local: str, os_values: set[OsName]) -> BackupItem:
    return {"path_local": path_local, "path_cloud": "^", "share_url": None, "zip": False, "encryption": None, "rel2home": True, "os": os_values}
