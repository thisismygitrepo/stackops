from difflib import unified_diff
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, TextArea

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupPlan


def cleanup_change_detail(*, change: CleanupChange) -> str:
    snapshot = change.snapshot
    if change.replacement is not None:
        original = snapshot.files[0].content.decode("utf-8")
        replacement = change.replacement.decode("utf-8")
        difference = "\n".join(unified_diff(
            original.splitlines(), replacement.splitlines(),
            fromfile=f"""Before: {snapshot.path}""", tofile=f"""After: {snapshot.path}""", lineterm="",
        ))
        return difference or f"""{snapshot.path}\n\nNo text changes."""
    if snapshot.directory:
        contents = [f"""Quarantine entire directory: {snapshot.path}""", ""]
        contents.extend(f"""Directory  {path}/""" for path, _mode in snapshot.directories)
        contents.extend(f"""File       {file.relative_path} ({len(file.content):,} bytes)""" for file in snapshot.files)
        contents.extend(f"""Symlink    {path} -> {target}""" for path, target in snapshot.links)
        return "\n".join(contents)
    if snapshot.links:
        return f"""Quarantine symlink: {snapshot.path}\n\nTarget: {snapshot.links[0][1]}"""
    content = snapshot.files[0].content
    try:
        text = content.decode("utf-8") if b"\x00" not in content else None
    except UnicodeDecodeError:
        text = None
    if text is None:
        text = f"""Binary or non-UTF-8 content ({len(content):,} bytes)."""
    return f"""Quarantine entire file: {snapshot.path}

{text}"""


class CleanupReview(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "dismiss(False)", "Cancel", priority=True)]
    CSS = """
    CleanupReview { align: center middle; }
    #cleanup-review {
        width: 94%; height: 92%; padding: 1 2;
        border: thick $warning; background: $surface;
    }
    #review-title { height: auto; text-style: bold; margin-bottom: 1; }
    #review-backup { height: auto; margin-bottom: 1; color: $text-muted; }
    #review-blockers { height: 6; border: solid $error; margin-bottom: 1; }
    #review-paths { height: 9; max-height: 35%; border: round $primary; }
    #review-detail { height: 1fr; min-height: 3; border: round $primary; }
    #review-actions { height: 3; align-horizontal: right; margin-top: 1; }
    #review-actions Button { margin-left: 1; }
    """

    def __init__(self, *, plan: CleanupPlan, backup_root: Path) -> None:
        super().__init__()
        self._cleanup_plan = plan
        self._backup_root = backup_root

    def compose(self) -> ComposeResult:
        plan = self._cleanup_plan
        with Vertical(id="cleanup-review"):
            yield Static(Text(f"""Review reset · {len(plan.entries)} resources · {len(plan.changes)} paths"""), id="review-title")
            yield Static(Text(f"""Originals and restore manifest will be saved in a new run directory under:
{self._backup_root}"""), id="review-backup")
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
            action = "Edit configuration" if change.replacement is not None else "Quarantine"
            table.add_row(Text(action), Text(str(change.snapshot.path)), key=str(index))
        detail = self.query_one("#review-detail", TextArea)
        detail.border_title = "Diff / quarantine contents"
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
