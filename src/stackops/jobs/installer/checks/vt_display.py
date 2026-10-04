from rich.panel import Panel
from rich.table import Table

from stackops.jobs.installer.checks.constants import VT_ACCOUNT_REQUEST_INTERVAL_SECONDS


def build_vt_parallelism_panel(account_count: int, concurrency: int) -> Panel:
    details = Table.grid(padding=(0, 2))
    details.add_row("Configured accounts", str(account_count))
    details.add_row("Concurrent files (maximum)", str(concurrency))
    details.add_row("Account request pacing", f"""One request every {VT_ACCOUNT_REQUEST_INTERVAL_SECONDS:g}s""")
    details.add_row("Account switching", "After account errors or exhausted retries")
    return Panel(details, title="VirusTotal", border_style="cyan", expand=False)
