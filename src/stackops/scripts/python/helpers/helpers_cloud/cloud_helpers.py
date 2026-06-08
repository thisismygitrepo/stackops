
from pathlib import Path
from rich.console import Console

console = Console()


def my_abs(path: str) -> Path:
    obj = Path(path).expanduser().absolute()
    if not path.startswith(".") and obj.absolute().exists():
        return obj
    try_absing = Path.cwd().joinpath(path)
    if try_absing.exists():
        return try_absing
    display_warning(f"Path {path} resolved to {obj} could not be resolved to absolute path.")
    display_warning("Trying to resolve symlinks (this may result in unintended paths).")
    return obj.absolute()


def display_header(title: str) -> None:
    console.print(f"\n[bold]{title}[/bold]")


def display_subheader(title: str) -> None:
    console.print(f"[bold]{title}[/bold]")


def display_content(content: str) -> None:
    console.print(content)


def display_status(status: str) -> None:
    console.print(status)


def display_success(message: str) -> None:
    console.print(f"[green]✓ {message}[/green]")


def display_warning(message: str) -> None:
    console.print(f"[yellow]⚠ {message}[/yellow]")


def display_error(message: str) -> None:
    console.print(f"[red]✗ {message}[/red]")
