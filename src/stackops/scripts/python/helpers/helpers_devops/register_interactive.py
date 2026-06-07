from collections.abc import Sequence

import typer
from rich.console import Console
from rich.panel import Panel


console = Console()


def _format_default(default: object | None) -> str:
    if default is None or default == "":
        return "(none)"
    return str(default)


def print_step(title: str, help_text: str, default: object | None = None) -> None:
    console.print(Panel(f"{help_text}\n\nDefault: {_format_default(default)}", title=title, border_style="cyan", padding=(1, 2)))


def ask_text(label: str, *, help_text: str, default: str | None = None, allow_empty: bool = False) -> str | None:
    print_step(title=label, help_text=help_text, default=default)
    while True:
        value = str(typer.prompt(label, default=default or "", show_default=default is not None and default != "")).strip()
        if value:
            return value
        if allow_empty:
            return None
        console.print("[red]This value is required.[/red]")


def ask_bool(label: str, *, help_text: str, default: bool) -> bool:
    print_step(title=label, help_text=help_text, default=default)
    return bool(typer.confirm(label, default=default))


def ask_choice(label: str, *, help_text: str, choices: Sequence[str], default: str) -> str:
    normalized_choices = tuple(choice.lower() for choice in choices)
    if default.lower() not in normalized_choices:
        raise ValueError(f"Default value {default!r} must be one of: {', '.join(choices)}")
    choice_help = f"{help_text}\n\nChoices: {', '.join(choices)}"
    while True:
        value = ask_text(label, help_text=choice_help, default=default)
        assert value is not None
        normalized_value = value.lower()
        if normalized_value in normalized_choices:
            return choices[normalized_choices.index(normalized_value)]
        console.print(f"[red]Choose one of: {', '.join(choices)}[/red]")


def confirm_summary(title: str, lines: Sequence[str]) -> None:
    console.print(Panel("\n".join(lines), title=title, border_style="green", padding=(1, 2)))
    if not typer.confirm("Create or update this entry?", default=True):
        raise typer.Exit(code=0)
