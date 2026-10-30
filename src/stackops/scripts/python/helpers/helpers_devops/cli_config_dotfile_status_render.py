from collections import Counter
from pathlib import Path

from rich import box
from rich.console import Group, RenderableType
from rich.filesize import decimal
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.profile.dotfiles_constants import ALL_OS_VALUES, OsName
from stackops.profile.dotfiles_mapper import LIBRARY_MAPPER_PATH, USER_MAPPER_PATH
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import format_home_relative_path
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data import Footprint, MapperCounts, MappersStatus, StorageStatus, SyncStatus
from stackops.utils.source_of_truth import DOTFILES_MAPPER_FILES_ROOT, DOTFILES_ROOT


def detail_table(*column_names: str) -> Table:
    table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 1))
    for column_name in column_names:
        table.add_column(column_name, overflow="fold")
    return table


def render_mappers(status: MappersStatus, expand: bool) -> Panel:
    table = detail_table("Mapper", "Path", "Groups", "Entries", *ALL_OS_VALUES)
    mappers: tuple[tuple[str, Path, MapperCounts | None], ...] = (
        ("Yours", USER_MAPPER_PATH, status.user_counts),
        ("Library", LIBRARY_MAPPER_PATH, status.library_counts),
    )
    for label, path, counts in mappers:
        if counts is None:
            table.add_row(label, Text(f"""{format_home_relative_path(path)} (missing)""", style="yellow"), *("-" for _ in range(2 + len(ALL_OS_VALUES))))
        else:
            table.add_row(label, format_home_relative_path(path), str(counts.groups), str(counts.entries), *(str(counts.entries_per_os[os_name]) for os_name in ALL_OS_VALUES))
    parts: list[RenderableType] = [table]
    if expand and len(status.user_group_counts) > 0:
        groups = detail_table("Your group", "Entries", *ALL_OS_VALUES)
        for group, counts in status.user_group_counts.items():
            groups.add_row(group, str(counts.entries), *(str(counts.entries_per_os[os_name]) for os_name in ALL_OS_VALUES))
        parts.append(groups)
    note = Text(f"""{len(status.replaced_library_entries)} library entries are replaced by entries in your mapper""", style="dim")
    if expand and len(status.replaced_library_entries) > 0:
        note.append(f""": {", ".join(f"{group}.{name}" for group, name in status.replaced_library_entries)}""")
    parts.append(note)
    return Panel(Group(*parts), title="🗂️ Mappers", border_style="cyan", expand=True)


def render_sync(status: SyncStatus, current_os: OsName, expand: bool) -> Panel:
    user_states = Counter(item.status for item in status.user)
    library_states = Counter(item.status for item in status.library)
    counts = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 2))
    for column_name in ("State", "Yours", "Library"):
        counts.add_column(column_name, justify="left" if column_name == "State" else "right")
    for state in sorted(user_states.keys() | library_states.keys(), key=lambda state: (state != "Configured", state)):
        counts.add_row(Text(state, style="green" if state == "Configured" else "yellow"), str(user_states[state]), str(library_states[state]))
    unsynced = [item for item in status.user if not item.configured]
    parts: list[RenderableType] = [counts]
    rows = [*(("yours", item) for item in status.user), *(("library", item) for item in status.library)] if expand else [("yours", item) for item in unsynced]
    if len(rows) > 0:
        details = detail_table("Entry", "State", "Original", "Managed")
        for source, item in rows:
            entry = Text(f"""{item.program}.{item.file_name}""", style="bold")
            entry.append(f"""\n{source} · {item.method}""", style="dim")
            state = Text(item.status, style="green" if item.configured else "yellow")
            details.add_row(entry, state, format_home_relative_path(Path(item.default_path)), format_home_relative_path(Path(item.managed_path)))
        parts.append(details)
    return Panel(
        Group(*parts),
        title=f"""🔗 Sync on {current_os} (yours: {user_states["Configured"]}/{len(status.user)} configured)""",
        border_style="green" if len(unsynced) == 0 else "yellow",
        expand=True,
    )


def render_storage(status: StorageStatus, expand: bool) -> Panel:
    grid = Table.grid(padding=(0, 2), expand=True)
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column(ratio=1, overflow="fold")
    match status.dotfiles_root_footprint:
        case None:
            grid.add_row(format_home_relative_path(DOTFILES_ROOT), Text("missing", style="yellow"))
        case Footprint() as footprint:
            grid.add_row(format_home_relative_path(DOTFILES_ROOT), f"""{footprint.files} files · {decimal(footprint.size_bytes)}, all of which export archives""")
    managed = status.managed_footprint
    grid.add_row("Your managed copies", f"""{len(status.managed_copies)} paths · {managed.files} files · {decimal(managed.size_bytes)}""")
    outside = Text("none", style="green")
    if len(status.outside_dotfiles_root) > 0:
        outside = Text("export does not carry these:", style="yellow")
        for group, name, managed_path in status.outside_dotfiles_root:
            outside.append(f"""\n{group}.{name}: {format_home_relative_path(managed_path)}""")
    grid.add_row(f"""Outside {format_home_relative_path(DOTFILES_ROOT)}""", outside)
    unreferenced = Text("none", style="green")
    if len(status.unreferenced_stored_paths) > 0:
        unreferenced = Text("no mapper entry points here:", style="yellow")
        for stored_path in status.unreferenced_stored_paths:
            unreferenced.append(f"""\n{stored_path.name}""")
    grid.add_row(f"""Unreferenced in {format_home_relative_path(DOTFILES_MAPPER_FILES_ROOT)}""", unreferenced)
    parts: list[RenderableType] = [grid]
    if expand and len(status.managed_copies) > 0:
        copies = detail_table("Managed copy", "Entries", "Files", "Size")
        for copy in status.managed_copies:
            entries = ", ".join(f"{group}.{name}" for group, name in copy.entries)
            copies.add_row(format_home_relative_path(copy.path), entries, str(copy.footprint.files), decimal(copy.footprint.size_bytes))
        parts.append(copies)
    return Panel(Group(*parts), title="💾 Storage", border_style="cyan", expand=True)
