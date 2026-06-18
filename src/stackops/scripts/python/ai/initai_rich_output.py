from pathlib import Path
from typing import Final

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.ai.initai_models import ArtifactAction, ArtifactChange, InitConfigPlan, InitConfigResult

_CONSOLE: Final[Console] = Console()
_ACTION_LABELS: Final[dict[ArtifactAction, tuple[str, str]]] = {
    "created": ("CREATE", "bold green"),
    "written": ("WRITE", "bold yellow"),
    "removed": ("REMOVE", "bold red"),
}


def _enabled_label(*, enabled: bool, enabled_text: str) -> Text:
    if enabled:
        return Text(f"● {enabled_text}", style="bold green")
    return Text("○ skipped", style="dim")


def _display_path(*, path: Path) -> Text:
    return Text(f"./{path.as_posix()}", style="bright_white")


def _artifact_purpose(*, path: Path) -> str:
    path_text = path.as_posix()
    if path_text == ".gitignore":
        return "Git exclusions"
    if path_text == ".vscode/tasks.json":
        return "Editor automation"
    if path_text.startswith("scripts/type_checking/"):
        return "Shared validation tooling"
    if path.name in {"AGENTS.md", "CLAUDE.md", "CLAUDE.local.md"}:
        return "Agent instructions"
    if "instructions" in path.parts or path.suffix == ".mdc":
        return "Agent instructions"
    return "Agent configuration"


def build_init_config_plan_panel(*, plan: InitConfigPlan) -> Panel:
    table = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Repository", Text(str(plan.repo_root), style="bright_white"))
    table.add_row("Agents", Text(", ".join(plan.frameworks), style="bold magenta"))
    table.add_row("Instructions", _enabled_label(enabled=plan.add_instructions, enabled_text="write agent instruction files"))
    table.add_row("Private config", _enabled_label(enabled=plan.add_private_config, enabled_text="write agent-specific config"))
    table.add_row("Shared scripts", _enabled_label(enabled=plan.include_common_scaffold, enabled_text="populate ./scripts/type_checking"))
    table.add_row("VS Code task", _enabled_label(enabled=plan.add_vscode_task, enabled_text="update ./.vscode/tasks.json"))
    table.add_row(
        "Git ignore", _enabled_label(enabled=plan.add_all_touched_configs_to_gitignore, enabled_text="add written config paths to ./.gitignore")
    )
    return Panel(
        table,
        title="[bold bright_cyan]◆ Agent configuration plan[/]",
        subtitle="[dim]filesystem changes are measured and reported[/]",
        border_style="bright_blue",
    )


def show_init_config_plan(*, plan: InitConfigPlan) -> None:
    _CONSOLE.print(build_init_config_plan_panel(plan=plan))


def create_phase_status(*, label: str, destination: str) -> Status:
    return _CONSOLE.status(f"[bold cyan]◆[/] {escape(label)} [dim]→ {escape(destination)}[/]", spinner="dots12", spinner_style="bright_cyan")


def show_phase_complete(*, label: str, destination: str, elapsed_seconds: float) -> None:
    _CONSOLE.print(f"[bold green]✓[/] {escape(label)} [dim]→ {escape(destination)} · {elapsed_seconds:.3f}s[/]")


def build_artifact_changes_table(*, changes: tuple[ArtifactChange, ...]) -> Table:
    table = Table(title=f"Filesystem changes ({len(changes)})", box=box.ROUNDED, header_style="bold bright_cyan", border_style="blue", expand=True)
    table.add_column("Action", no_wrap=True, width=8)
    table.add_column("File", ratio=3, overflow="fold")
    table.add_column("Purpose", ratio=2, overflow="fold")
    for change in changes:
        action_label, action_style = _ACTION_LABELS[change.action]
        table.add_row(
            Text(action_label, style=action_style), _display_path(path=change.path), Text(_artifact_purpose(path=change.path), style="cyan")
        )
    return table


def build_init_config_result_panel(*, result: InitConfigResult) -> Panel:
    action_counts: dict[ArtifactAction, int] = {"created": 0, "written": 0, "removed": 0}
    for change in result.artifact_changes:
        action_counts[change.action] += 1

    summary = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    summary.add_column("Field", style="bold green", no_wrap=True)
    summary.add_column("Value")
    summary.add_row("Agents configured", Text(", ".join(result.plan.frameworks), style="bold magenta"))
    summary.add_row("Created", Text(str(action_counts["created"]), style="bold green"))
    summary.add_row("Written", Text(str(action_counts["written"]), style="bold yellow"))
    summary.add_row("Removed", Text(str(action_counts["removed"]), style="bold red"))
    summary.add_row("Elapsed", Text(f"{result.elapsed_seconds:.3f}s", style="bright_white"))
    return Panel(summary, title="[bold green]✓ Configuration complete[/]", border_style="green")


def show_init_config_result(*, result: InitConfigResult) -> None:
    _CONSOLE.print(build_init_config_result_panel(result=result))
    if len(result.artifact_changes) == 0:
        _CONSOLE.print(Panel("[dim]No files were created, rewritten, or removed.[/]", title="Filesystem changes", border_style="yellow"))
        return
    _CONSOLE.print(build_artifact_changes_table(changes=result.artifact_changes))
