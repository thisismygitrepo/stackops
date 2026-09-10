from collections import Counter
from datetime import date
from pathlib import Path

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_activity import SecondBrainGitActivity
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_constants import (
    AGENT_DISPLAY_NAME,
    NON_RESUMABLE_SESSION_IDS,
)
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_progress import show_second_brain_progress
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_records import UpdateFile


def show_second_brain_status(
    *, second_brain_root: Path, update_files: list[UpdateFile], git_activity: SecondBrainGitActivity, today: date
) -> None:
    console = Console()
    records = [record for update_file in update_files for record in update_file.records]
    invalid_row_count = sum(len(update_file.invalid_rows) for update_file in update_files)
    invalid_file_count = sum(update_file.error is not None for update_file in update_files)
    unavailable_session_count = sum(record.session_id.casefold() in NON_RESUMABLE_SESSION_IDS for record in records)
    sessions = {
        (record.agent, record.session_id)
        for record in records
        if record.session_id.casefold() not in NON_RESUMABLE_SESSION_IDS
    }
    work_items_root = second_brain_root.joinpath("work-items")
    work_items = {update_file.path.parent for update_file in update_files if update_file.path.parent.is_relative_to(work_items_root)}
    dates = [record.updated_on for record in records]

    status_style = "red" if invalid_file_count else "yellow" if invalid_row_count else "green"
    status_label = (
        "Update logs need correction" if invalid_file_count else "Invalid updates found" if invalid_row_count else "All updates valid"
    )
    console.print(
        Panel(
            Group(Text(str(second_brain_root), style="dim", overflow="fold"), Text(status_label, style=f"""bold {status_style}""")),
            title=Text("Second Brain status", style="bold"),
            title_align="left",
            border_style=status_style,
            padding=(0, 1),
        )
    )
    show_second_brain_progress(
        console=console, second_brain_root=second_brain_root, update_files=update_files, git_activity=git_activity, today=today
    )

    summary = Table(title="Overview", box=box.ROUNDED, show_header=False, border_style="dim", title_style="bold cyan")
    summary.add_column("Statistic", overflow="fold")
    summary.add_column("Value", justify="right", style="bold")
    summary.add_row("Update logs", str(len(update_files)))
    summary.add_row("Invalid update logs", Text(str(invalid_file_count), style="red" if invalid_file_count else "dim"))
    summary.add_row("Recorded work items", str(len(work_items)))
    summary.add_section()
    summary.add_row("Total updates", str(len(records) + invalid_row_count))
    summary.add_row("Valid updates", Text(str(len(records)), style="green"))
    summary.add_row("Invalid updates", Text(str(invalid_row_count), style="yellow" if invalid_row_count else "dim"))
    summary.add_section()
    summary.add_row("Unique resumable sessions", str(len(sessions)))
    summary.add_row("Updates without resumable sessions", str(unavailable_session_count))
    summary.add_section()
    summary.add_row("Earliest update", min(dates).isoformat() if dates else "-")
    summary.add_row("Latest update", max(dates).isoformat() if dates else "-")

    agent_rows = Counter(record.agent for record in records)
    agents = Table(title="Valid updates by agent", box=box.ROUNDED, border_style="dim", title_style="bold cyan", header_style="bold cyan")
    agents.add_column("Agent", overflow="fold")
    agents.add_column("Updates", justify="right", style="bold")
    for agent, display_name in AGENT_DISPLAY_NAME.items():
        agents.add_row(Text(display_name), str(agent_rows[agent]))
    console.print(Columns([summary, agents], padding=(0, 2)))
    if invalid_file_count:
        console.print(Text("Update totals exclude invalid logs.", style="dim"))

    if invalid_row_count or invalid_file_count:
        console.print()
        console.rule(Text("Invalid updates", style="bold yellow"), style="dim")
        for update_file in update_files:
            if update_file.error is None and not update_file.invalid_rows:
                continue
            issues = Table(box=box.SIMPLE_HEAD, expand=True, header_style="bold", padding=(0, 1))
            issues.add_column("Line", justify="right", no_wrap=True)
            issues.add_column("Problem", overflow="fold", ratio=1)
            if update_file.error is not None:
                issues.add_row("-", Text(update_file.error, style="red", overflow="fold"))
            for invalid_row in update_file.invalid_rows:
                issues.add_row(str(invalid_row.line_number), Text(invalid_row.reason, overflow="fold"))
            console.print(
                Panel(
                    Group(Text(str(update_file.path.relative_to(second_brain_root)), style="bold", overflow="fold"), issues),
                    border_style="red" if update_file.error is not None else "yellow",
                    padding=(0, 1),
                )
            )


def show_second_brain_align_result(
    *, second_brain_root: Path, removed_rows: dict[Path, int], scanned_file_count: int, force: bool
) -> None:
    console = Console()
    action = "Removed" if force else "Would remove"
    removed_row_count = sum(removed_rows.values())
    result_style = "yellow" if removed_row_count and not force else "green"
    result_message = (
        f"""{action} {removed_row_count} invalid updates from {len(removed_rows)} of {scanned_file_count} update logs."""
        if removed_row_count
        else f"""No invalid updates found across {scanned_file_count} update logs."""
    )
    console.print(
        Panel(
            Group(Text(str(second_brain_root), style="dim", overflow="fold"), Text(result_message, style=f"""bold {result_style}""")),
            title=Text("Alignment applied" if force else "Alignment preview", style="bold"),
            title_align="left",
            border_style=result_style,
            padding=(0, 1),
        )
    )
    if removed_rows:
        changes = Table(box=box.ROUNDED, border_style="dim", header_style="bold cyan", expand=True)
        changes.add_column("File", overflow="fold", ratio=1)
        changes.add_column("Updates removed" if force else "Updates to remove", justify="right", style=result_style)
        for update_path, row_count in sorted(removed_rows.items()):
            changes.add_row(Text(str(update_path.relative_to(second_brain_root)), overflow="fold"), str(row_count))
        console.print(changes)
        if not force:
            console.print(Text.assemble("To delete these updates, run: ", ("agents B align --force", "bold cyan")))
