from collections import Counter
from pathlib import Path
from typing import assert_never, cast, get_args

from rich import box
from rich.console import Group, RenderableType
from rich.filesize import decimal
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.profile.dotfiles_collect_plan import CollectEntryPlan, VerdictCategory, verdict_category
from stackops.profile.dotfiles_constants import ALL_OS_VALUES, STATUS_DETAIL_ROW_LIMIT
from stackops.profile.dotfiles_mapper import LIBRARY_MAPPER_PATH, USER_MAPPER_PATH
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_collect import describe_verdict
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import format_home_relative_path
from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data import DotfilesStatus, Footprint, MapperCounts
from stackops.utils.source_of_truth import DOTFILES_MAPPER_FILES_ROOT, DOTFILES_ROOT


def _describe_category(category: VerdictCategory) -> str:
    match category:
        case "tracked":
            return "in your mapper"
        case "collectable":
            return "collectable"
        case "skipped":
            return "skipped by collect"
        case "packaged":
            return "same as the packaged settings"
        case "absent":
            return "not on this machine"
        case "other_os":
            return "for another OS"
        case _:
            assert_never(category)


def _detail_table(*column_names: str) -> Table:
    table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 1), expand=True)
    for column_name in column_names:
        table.add_column(column_name, overflow="fold")
    return table


def render_mappers(status: DotfilesStatus) -> Panel:
    table = _detail_table("Mapper", "Path", "Groups", "Entries", *ALL_OS_VALUES)
    mappers: tuple[tuple[str, Path, MapperCounts | None], ...] = (
        ("Yours", USER_MAPPER_PATH, status.user_counts),
        ("Library", LIBRARY_MAPPER_PATH, status.library_counts),
    )
    for label, path, counts in mappers:
        if counts is None:
            table.add_row(label, Text(f"""{format_home_relative_path(path)} (missing)""", style="yellow"), *("-" for _ in range(2 + len(ALL_OS_VALUES))))
        else:
            table.add_row(label, format_home_relative_path(path), str(counts.groups), str(counts.entries), *(str(counts.entries_per_os[os_name]) for os_name in ALL_OS_VALUES))
    note = Text(f"""{status.replaced_library_entries} library entries are replaced by entries in your mapper.""", style="dim")
    return Panel(Group(table, note), title="🗂️ Mappers", border_style="cyan", expand=True)


def render_sync(status: DotfilesStatus) -> Panel:
    user_states = Counter(item.status for item in status.user_sync)
    library_states = Counter(item.status for item in status.library_sync)
    counts = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 2))
    for column_name in ("State", "Yours", "Library"):
        counts.add_column(column_name, justify="left" if column_name == "State" else "right")
    for state in sorted(user_states.keys() | library_states.keys(), key=lambda state: (state != "Configured", state)):
        counts.add_row(Text(state, style="green" if state == "Configured" else "yellow"), str(user_states[state]), str(library_states[state]))
    unsynced = [item for item in status.user_sync if not item.configured]
    parts: list[RenderableType] = [counts]
    if len(unsynced) > 0:
        details = _detail_table("Your entry", "State", "Original", "Managed")
        for item in unsynced:
            details.add_row(f"""{item.program}.{item.file_name}""", Text(item.status, style="yellow"), format_home_relative_path(Path(item.default_path)), format_home_relative_path(Path(item.managed_path)))
        parts.append(details)
    configured = user_states["Configured"]
    return Panel(
        Group(*parts),
        title=f"""🔗 Sync on {status.current_os} (yours: {configured}/{len(status.user_sync)} configured)""",
        border_style="green" if len(unsynced) == 0 else "yellow",
        expand=True,
    )


def render_radar(status: DotfilesStatus) -> Panel:
    categories: Counter[VerdictCategory] = Counter(verdict_category(plan.verdict) for plan in status.radar)
    ordered_categories = cast(tuple[VerdictCategory, ...], get_args(VerdictCategory.__value__))
    summary = Text(" · ".join(f"""{categories[category]} {_describe_category(category)}""" for category in ordered_categories if categories[category] > 0), style="dim")
    untracked: list[CollectEntryPlan] = [plan for plan in status.radar if verdict_category(plan.verdict) in ("collectable", "skipped")]
    parts: list[RenderableType] = [summary]
    if 0 < len(untracked) <= STATUS_DETAIL_ROW_LIMIT:
        details = _detail_table("Group", "Entry", "Original", "Collect would")
        for plan in untracked:
            details.add_row(plan.group, plan.name, format_home_relative_path(plan.original_path), describe_verdict(plan.verdict))
        parts.append(details)
    elif len(untracked) > STATUS_DETAIL_ROW_LIMIT:
        details = _detail_table("Group", "Entries", "Collect would")
        for group in dict.fromkeys(plan.group for plan in untracked):
            group_plans = [plan for plan in untracked if plan.group == group]
            details.add_row(group, ", ".join(plan.name for plan in group_plans), "; ".join(dict.fromkeys(describe_verdict(plan.verdict) for plan in group_plans)))
        parts.append(details)
    collectable_groups = list(dict.fromkeys(plan.group for plan in untracked if verdict_category(plan.verdict) == "collectable"))
    if len(collectable_groups) > 0:
        parts.append(Text(f"""Collect with: devops config dotfiles collect --which {",".join(collectable_groups)}""", style="dim"))
    return Panel(
        Group(*parts),
        title=f"""📡 Known dotfiles on {status.current_os} not in your mapper ({categories["collectable"]} collectable, {categories["skipped"]} skipped)""",
        border_style="green" if len(untracked) == 0 else "yellow",
        expand=True,
    )


def render_storage(status: DotfilesStatus) -> Panel:
    grid = Table.grid(padding=(0, 2), expand=True)
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column(ratio=1, overflow="fold")
    match status.dotfiles_root_footprint:
        case None:
            grid.add_row(format_home_relative_path(DOTFILES_ROOT), Text("missing", style="yellow"))
        case Footprint() as footprint:
            grid.add_row(format_home_relative_path(DOTFILES_ROOT), f"""{footprint.files} files · {decimal(footprint.size_bytes)}, all of which export archives""")
    grid.add_row("Your managed copies", f"""{status.managed_path_count} paths · {status.managed_footprint.files} files · {decimal(status.managed_footprint.size_bytes)}""")
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
    return Panel(grid, title="💾 Storage", border_style="cyan", expand=True)
