from datetime import date, timedelta
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_activity import SecondBrainGitActivity
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_records import UpdateFile


def show_second_brain_progress(
    *,
    console: Console,
    second_brain_root: Path,
    update_files: list[UpdateFile],
    git_activity: SecondBrainGitActivity,
    today: date,
) -> None:
    week_start = today - timedelta(days=today.weekday())
    cutoffs = (today, week_start)
    update_dates = [record.updated_on for update_file in update_files for record in update_file.records]
    work_items_root = second_brain_root.joinpath("work-items")
    work_item_dates = {
        update_file.path.parent: [record.updated_on for record in update_file.records]
        for update_file in update_files
        if update_file.records and update_file.path.parent.is_relative_to(work_items_root)
    }
    updates = [sum(cutoff <= updated_on <= today for updated_on in update_dates) for cutoff in cutoffs]
    active_work_items = [
        sum(any(cutoff <= updated_on <= today for updated_on in dates) for dates in work_item_dates.values())
        for cutoff in cutoffs
    ]
    first_logged_work_items = [
        sum(cutoff <= min(dates) <= today for dates in work_item_dates.values()) for cutoff in cutoffs
    ]

    progress = Table(
        box=box.ROUNDED,
        border_style="dim",
        header_style="bold cyan",
        expand=True,
        caption=Text(
            f"""Week starts Monday, {week_start.isoformat()}. File and line counts show committed changes.""",
            style="dim",
        ),
    )
    progress.add_column("Progress", overflow="fold", ratio=1)
    progress.add_column("Today", justify="right", style="bold")
    progress.add_column("This week", justify="right", style="bold")
    progress.add_row("Updates", str(updates[0]), str(updates[1]))
    progress.add_row("Active work items", str(active_work_items[0]), str(active_work_items[1]))
    progress.add_row("Work items first logged", str(first_logged_work_items[0]), str(first_logged_work_items[1]))
    progress.add_section()
    progress.add_row("Commits", str(git_activity.today.commits), str(git_activity.this_week.commits))
    progress.add_row("Files changed", str(git_activity.today.files_changed), str(git_activity.this_week.files_changed))
    progress.add_row("Files added", str(git_activity.today.files_added), str(git_activity.this_week.files_added))
    progress.add_row(
        "Lines added",
        Text(f"""+{git_activity.today.lines_added}""", style="green"),
        Text(f"""+{git_activity.this_week.lines_added}""", style="green"),
    )
    progress.add_row(
        "Lines removed",
        Text(f"""-{git_activity.today.lines_deleted}""", style="red"),
        Text(f"""-{git_activity.this_week.lines_deleted}""", style="red"),
    )
    console.print()
    console.print(progress)
    console.print(
        Text.assemble(
            ("Uncommitted files: ", "bold"),
            (f"""{git_activity.working_tree.new_files} new""", "green"),
            " · ",
            (f"""{git_activity.working_tree.changed_files} changed""", "yellow"),
            " · ",
            (f"""{git_activity.working_tree.deleted_files} deleted""", "red"),
        )
    )
