import platform

import psutil
from rich import box
from rich.console import Console
from rich.filesize import decimal
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_local.vllm import VllmStatus


def show_vllm_doctor(*, status: VllmStatus) -> None:
    console = Console()
    reachable = status.healthy or status.version is not None or status.models is not None or status.metrics is not None
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

    overview = Table(title="vLLM", box=box.ROUNDED, show_header=False)
    overview.add_column("Statistic")
    overview.add_column("Value", overflow="fold")
    overview.add_row("CLI on this machine", Text(status.cli_path or "Not installed / not on PATH"))
    overview.add_row("Server", Text(status.host))
    overview.add_row("OpenAI API base", Text(f"""{status.host}/v1"""))
    overview.add_row("Health check", "Passed" if status.healthy else "Failed")
    overview.add_row("Server version", Text(status.version or "Unknown"))
    overview.add_row("Served models / adapters", "Unknown" if status.models is None else str(len(status.models)))
    metrics = status.metrics
    overview.add_row("Running requests", "Unknown" if metrics is None or metrics.running_requests is None else f"""{metrics.running_requests:g}""")
    overview.add_row("Waiting requests", "Unknown" if metrics is None or metrics.waiting_requests is None else f"""{metrics.waiting_requests:g}""")
    overview.add_row("Peak KV cache usage", "Unknown" if metrics is None or metrics.peak_kv_cache_usage is None else f"""{metrics.peak_kv_cache_usage:.1%}""")
    console.print(overview)

    if status.models:
        models = Table(title="Served models / adapters", box=box.ROUNDED, header_style="bold cyan")
        for column in ("Model", "Context", "Source", "Parent"):
            models.add_column(column, overflow="fold")
        for model in sorted(status.models, key=lambda item: item.name):
            models.add_row(
                Text(model.name), "-" if model.max_model_len is None else f"""{model.max_model_len:,}""",
                Text(model.root or "-"), Text(model.parent or "-"),
            )
        console.print(models)
    elif status.models is not None:
        console.print(Text("No models advertised by this vLLM server. Start one with: agents local serve <model>", style="yellow"))

    if status.errors:
        console.print(Panel(Text("\n".join(status.errors)), title="vLLM checks failed", border_style="red"))
        if not reachable:
            console.print(Text("Start vLLM with 'agents local serve <model>'; check --host / VLLM_BASE_URL.", style="yellow"))
            if status.cli_path is None:
                console.print(Text("Install vLLM with: agents local install", style="yellow"))
