from rich.panel import Panel
from rich.table import Table


def build_vt_parallelism_panel(api_key_count: int, worker_count: int, apps_per_key: int) -> Panel:
    details = Table.grid(padding=(0, 2))
    details.add_row("API keys available", str(api_key_count))
    details.add_row("API keys in use", str(min(api_key_count, worker_count)))
    details.add_row("Apps per key (configured)", str(apps_per_key))
    details.add_row("Concurrent scans (maximum)", str(worker_count))
    details.add_row("Requests per key", "1 at a time")
    return Panel(details, title="VirusTotal", border_style="cyan", expand=False)
