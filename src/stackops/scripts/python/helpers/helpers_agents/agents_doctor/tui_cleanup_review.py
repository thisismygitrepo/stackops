from difflib import unified_diff

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, TextArea

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupEdit, CleanupPlan, CleanupRemoval


def cleanup_change_detail(*, change: CleanupChange) -> str:
    path = change.path
    match change:
        case CleanupEdit():
            difference = "\n".join(unified_diff(
                change.original.decode("utf-8").splitlines(), change.replacement.decode("utf-8").splitlines(),
                fromfile=f"""Before: {path}""", tofile=f"""After: {path}""", lineterm="",
            ))
            return difference or f"""{path}\n\nNo text changes."""
        case CleanupRemoval():
            if path.is_symlink():
                return f"""Delete symlink: {path}\n\nTarget: {path.readlink()}"""
            if path.is_dir():
                children = [f"""{child.name}/""" if child.is_dir() and not child.is_symlink() else child.name for child in sorted(path.iterdir())]
                return "\n".join([f"""Delete entire directory: {path}""", "", *children])
            return f"""Delete entire file: {path}"""


class CleanupReview(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "dismiss(False)", "Cancel", priority=True)]
    CSS = """
    CleanupReview { align: center middle; }
    #cleanup-review {
        width: 94%; height: 92%; padding: 1 2;
        border: thick $warning; background: $surface;
    }
    #review-title { height: auto; text-style: bold; margin-bottom: 1; }
    #review-warning { height: auto; margin-bottom: 1; color: $text-muted; }
    #review-blockers { height: 6; border: solid $error; margin-bottom: 1; }
    #review-paths { height: 9; max-height: 35%; border: round $primary; }
    #review-detail { height: 1fr; min-height: 3; border: round $primary; }
    #review-actions { height: 3; align-horizontal: right; margin-top: 1; }
    #review-actions Button { margin-left: 1; }
    """

    def __init__(self, *, plan: CleanupPlan) -> None:
        super().__init__()
        self._cleanup_plan = plan

    def compose(self) -> ComposeResult:
        plan = self._cleanup_plan
        with Vertical(id="cleanup-review"):
            yield Static(Text(f"""Review reset · {len(plan.entries)} resources · {len(plan.changes)} paths"""), id="review-title")
            yield Static(Text("Deleted paths are removed permanently; nothing is backed up."), id="review-warning")
            if plan.blockers:
                yield TextArea("\n".join(plan.blockers), read_only=True, id="review-blockers")
            yield DataTable[Text](cursor_type="row", id="review-paths")
            yield TextArea(read_only=True, soft_wrap=False, show_line_numbers=False, id="review-detail")
            with Horizontal(id="review-actions"):
                yield Button("Cancel", id="review-cancel")
                yield Button(
                    "Apply reset", variant="error", id="review-apply",
                    disabled=bool(plan.blockers) or not plan.changes,
                )

    def on_mount(self) -> None:
        table = self.query_one("#review-paths", DataTable)
        table.border_title = "Planned changes · arrows to inspect"
        table.add_columns("Action", "Path")
        for index, change in enumerate(self._cleanup_plan.changes):
            action = "Delete" if isinstance(change, CleanupRemoval) else "Edit configuration"
            table.add_row(Text(action), Text(str(change.path)), key=str(index))
        detail = self.query_one("#review-detail", TextArea)
        detail.border_title = "Diff / deletion"
        if self._cleanup_plan.changes:
            detail.load_text(cleanup_change_detail(change=self._cleanup_plan.changes[0]))
        else:
            detail.load_text("No paths will change.")
        if self._cleanup_plan.blockers:
            self.query_one("#review-blockers", TextArea).border_title = "Reset blocked"
        self.query_one("#review-cancel", Button).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        event.stop()
        self.query_one("#review-detail", TextArea).load_text(
            cleanup_change_detail(change=self._cleanup_plan.changes[event.cursor_row]),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "review-cancel":
            self.dismiss(False)
        elif event.button.id == "review-apply" and not self._cleanup_plan.blockers and self._cleanup_plan.changes:
            self.dismiss(True)
