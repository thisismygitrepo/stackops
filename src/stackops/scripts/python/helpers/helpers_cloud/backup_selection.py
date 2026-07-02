from dataclasses import dataclass

from stackops.scripts.python.helpers.helpers_cloud.backup_config import BackupConfig


@dataclass(frozen=True)
class BackupEntryKey:
    group_name: str
    item_name: str


def parse_backup_entry_selectors(which: str) -> tuple[str, ...]:
    selectors = tuple(token.strip() for token in which.split(","))
    if not selectors or any(not selector for selector in selectors):
        raise ValueError("Invalid --which value: expected a comma-separated list of non-empty group or group.item names, or 'all'.")
    if "all" in selectors and selectors != ("all",):
        raise ValueError("Invalid --which value: 'all' cannot be combined with other entries.")
    return selectors


def resolve_backup_entry_keys(*, config: BackupConfig, selectors: tuple[str, ...]) -> list[BackupEntryKey]:
    if selectors == ("all",):
        return [
            BackupEntryKey(group_name=group_name, item_name=item_name)
            for group_name, group_items in config.items()
            for item_name in group_items
        ]

    selected_keys: list[BackupEntryKey] = []
    selected_key_set: set[BackupEntryKey] = set()
    unknown_selectors: list[str] = []
    for selector in selectors:
        if selector in config:
            matching_keys = [BackupEntryKey(group_name=selector, item_name=item_name) for item_name in config[selector]]
        elif "." in selector:
            group_name, item_name = selector.split(".", 1)
            if group_name in config and item_name in config[group_name]:
                matching_keys = [BackupEntryKey(group_name=group_name, item_name=item_name)]
            else:
                unknown_selectors.append(selector)
                continue
        else:
            unknown_selectors.append(selector)
            continue
        for matching_key in matching_keys:
            if matching_key not in selected_key_set:
                selected_keys.append(matching_key)
                selected_key_set.add(matching_key)

    if unknown_selectors:
        raise ValueError(f"Unknown backup entries: {', '.join(unknown_selectors)}")
    if not selected_keys:
        raise ValueError("No backup entries selected.")
    return selected_keys
