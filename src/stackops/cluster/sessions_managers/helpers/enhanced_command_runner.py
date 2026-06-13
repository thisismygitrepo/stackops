#!/usr/bin/env python3
"""Enhanced command execution utilities with Rich formatting."""

import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def run_enhanced_command(
    command: str,
    description: str | None,
    show_progress: bool,
    timeout: int | None,
) -> dict[str, object]:
    if description is None:
        description = f"Executing: {command[:50]}..."

    try:
        if show_progress:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                task = progress.add_task(f"[cyan]{description}[/cyan]", total=None)

                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)

                progress.update(task, completed=True)
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)

        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""

        if "Session:" in stdout and "successfully deleted" in stdout:
            console.print(f"[bold red]{stdout}[/bold red]")

        if "Pseudo-terminal will not be allocated" in stderr:
            console.print("[dim yellow]ℹ️  Note: Running in non-interactive mode[/dim yellow]")
            stderr = stderr.replace("Pseudo-terminal will not be allocated because stdin is not a terminal.\n", "")

        if result.returncode == 0:
            if stdout and "Session:" not in stdout:
                console.print(f"[green]{stdout}[/green]")
            return {"success": True, "returncode": result.returncode, "stdout": stdout, "stderr": stderr}
        else:
            if stderr:
                console.print(f"[bold red]Error:[/bold red] [red]{stderr}[/red]")
            return {"success": False, "returncode": result.returncode, "stdout": stdout, "stderr": stderr}

    except subprocess.TimeoutExpired:
        console.print(f"[bold red]⏰ Command timed out after {timeout} seconds[/bold red]")
        return {"success": False, "error": "Timeout", "timeout": timeout}
    except Exception as exc:
        console.print(f"[bold red]💥 Unexpected error:[/bold red] [red]{str(exc)}[/red]")
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    # Demo the enhanced command execution
    console.print(Panel.fit("🎨 Enhanced Command Execution Demo", style="bold cyan"))

    # Test with a simple command
    result = run_enhanced_command("echo 'Hello, Rich world!'", "Testing enhanced output", True, None)
    console.print(f"Result: {result}")
