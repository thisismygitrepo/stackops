from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_devops.mount_helpers.utils import format_device


def pick_device(entries: list[DeviceEntry], header: str) -> DeviceEntry:
    from stackops.utils.options_utils.options import choose_from_options

    options: list[str] = []
    map_option: dict[str, DeviceEntry] = {}
    for idx, entry in enumerate(entries):
        option = f"{idx:02d} {format_device(entry)}"
        options.append(option)
        map_option[option] = entry
    choice = choose_from_options(options=options, msg="Select a device", multi=False, header=header, tv=True)
    if choice is None:
        raise RuntimeError("Device selection cancelled")
    selected = map_option.get(choice)
    if selected is None:
        raise RuntimeError("Selection not found")
    return selected


def resolve_device(entries: list[DeviceEntry], query: str) -> DeviceEntry:
    query_value = query.strip()
    if query_value in {"?", ""}:
        raise RuntimeError("Provide an exact device path, key, or label, or use --interactive.")
    exact_matches = [
        entry
        for entry in entries
        if entry.device_path.lower() == query_value.lower()
        or entry.key.lower() == query_value.lower()
        or (entry.label is not None and entry.label.lower() == query_value.lower())
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise RuntimeError("Multiple devices match; specify an exact device path or use --interactive.")
    raise RuntimeError("No exact device match; use utils machine list-devices --json for identifiers.")
