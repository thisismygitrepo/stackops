import platform

import psutil
from rich import box
from rich.console import Console
from rich.filesize import decimal
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_local.ollama import OllamaStatus


def show_local_doctor(*, status: OllamaStatus) -> None:
    console = Console()
    reachable = status.version is not None or status.models is not None or status.running_models is not None
    health = "Ready" if not status.errors else "Incomplete" if reachable else "Unavailable"
    health_style = "green" if not status.errors else "yellow" if reachable else "red"
    console.print(Panel(Text(health, style=health_style), title="Local model doctor", border_style=health_style))

    memory = psutil.virtual_memory()
    machine = Table(title="This machine", box=box.ROUNDED, show_header=False)
    machine.add_column("Resource")
    machine.add_column("Value", overflow="fold")
    machine.add_row("System", Text(f"""{platform.system()} {platform.release()} ({platform.machine()})"""))
    machine.add_row("CPU cores (logical)", str(psutil.cpu_count(logical=True) or "Unknown"))
    machine.add_row("RAM total", decimal(memory.total))
    machine.add_row("RAM available", decimal(memory.available))
    console.print(machine)

    overview = Table(title="Ollama", box=box.ROUNDED, show_header=False)
    overview.add_column("Statistic")
    overview.add_column("Value", overflow="fold")
    overview.add_row("CLI on this machine", Text(status.cli_path or "Not installed / not on PATH"))
    overview.add_row("Server", Text(status.host))
    overview.add_row("Server version", Text(status.version or "Unknown"))
    downloaded = None if status.models is None else tuple(model for model in status.models if not model.remote)
    overview.add_row("Downloaded models", "Unknown" if downloaded is None else str(len(downloaded)))
    overview.add_row("Aggregate model sizes", "Unknown" if downloaded is None else decimal(sum(model.size for model in downloaded)))
    if status.models is not None:
        overview.add_row("Cloud model entries", str(sum(model.remote for model in status.models)))
    running = status.running_models
    overview.add_row("Loaded models", "Unknown" if running is None else str(len(running)))
    overview.add_row("Loaded model memory", "Unknown" if running is None else decimal(sum(model.size for model in running)))
    overview.add_row("Loaded model VRAM", "Unknown" if running is None else decimal(sum(model.size_vram for model in running)))
    console.print(overview)

    if downloaded:
        models = Table(title="Downloaded models", box=box.ROUNDED, header_style="bold cyan")
        for column in ("Model", "Size", "Family", "Parameters", "Quantization", "Modified"):
            models.add_column(column, overflow="fold")
        for model in sorted(downloaded, key=lambda item: item.name):
            models.add_row(
                Text(model.name),
                decimal(model.size),
                Text(model.family or "-"),
                Text(model.parameter_size or "-"),
                Text(model.quantization_level or "-"),
                Text(model.modified_at.partition("T")[0] or "-"),
            )
        console.print(models)
    elif downloaded is not None:
        console.print(Text("No local models downloaded. Download one with: ollama pull <model>", style="yellow"))

    if running:
        loaded = Table(title="Loaded models", box=box.ROUNDED, header_style="bold cyan")
        for column in ("Model", "Memory", "VRAM", "Context", "Expires"):
            loaded.add_column(column, overflow="fold")
        for running_model in sorted(running, key=lambda item: item.name):
            loaded.add_row(
                Text(running_model.name),
                decimal(running_model.size),
                decimal(running_model.size_vram),
                "-" if running_model.context_length is None else f"""{running_model.context_length:,}""",
                Text(running_model.expires_at or "-"),
            )
        console.print(loaded)
    elif running is not None:
        console.print(Text("No models currently loaded in memory.", style="dim"))

    if status.errors:
        console.print(Panel(Text("\n".join(status.errors)), title="Ollama checks failed", border_style="red"))
        if not reachable:
            console.print(Text("Start Ollama with 'ollama serve' or open the Ollama app; check --host / OLLAMA_HOST.", style="yellow"))
            if status.cli_path is None:
                console.print(Text("Install Ollama if needed: https://ollama.com/download", style="yellow"))
