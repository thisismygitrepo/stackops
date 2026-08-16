from collections.abc import Sequence

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import REMOTE_DEBUGGING_LAN
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    BrowserLaunchResult,
    DetachedBrowserLaunchResult,
    ExistingBrowserLaunchResult,
    TmuxBrowserLaunchResult,
)
from stackops.utils.network.address import InterfaceIPv4Address


def build_browser_launch_summary(*, result: BrowserLaunchResult, lan_address: InterfaceIPv4Address | None) -> Group:
    lan_exposed = result.host == REMOTE_DEBUGGING_LAN
    if lan_exposed != (lan_address is not None):
        raise ValueError("A selected LAN address is required exactly when the browser endpoint is exposed to the LAN")

    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white", overflow="fold")

    match result:
        case ExistingBrowserLaunchResult():
            title = Text(f"✓ {result.process_label} ready", style="bold green")
            table.add_row("Process", Text(f"PID {result.process_id} · existing {result.owner}"))
            if result.opened_page:
                table.add_row("Action", Text("Opened a page because the endpoint had no page targets"))
            if result.repaired_relay:
                table.add_row("Action", Text("Restarted the missing LAN relay"))
        case DetachedBrowserLaunchResult():
            title = Text(f"✓ {result.process_label} launched", style="bold green")
            table.add_row("Process", Text(f"PID {result.process_id} · detached"))
            if result.relay_process_id is not None:
                table.add_row("Relay", Text(f"PID {result.relay_process_id} → 127.0.0.1:{result.browser_port}"))
        case TmuxBrowserLaunchResult():
            title = Text(f"✓ {result.process_label} launched", style="bold green")
            table.add_row("Process", Text(f"tmux · session {result.tmux.session_name}"))
            table.add_row("Browser window", Text(result.tmux.browser_window_name))
            if result.tmux.relay_window_name is not None:
                table.add_row("Relay window", Text(f"{result.tmux.relay_window_name} → 127.0.0.1:{result.browser_port}"))
            table.add_row("Attach", Text(" ".join(result.tmux.attach_command)))

    table.add_row("Executable", Text(str(result.browser_path)))
    endpoint_label = result.endpoint_short_label if not lan_exposed else f"{result.endpoint_short_label} bind"
    table.add_row(endpoint_label, Text(f"{result.host}:{result.port}"))
    if lan_address is not None:
        lan_endpoint = f"http://{lan_address.ipv4_address}:{result.port}"
        lan_endpoint_text = Text(lan_endpoint, style="bold bright_blue")
        lan_endpoint_text.stylize(f"link {lan_endpoint}")
        lan_endpoint_text.append(f" · {lan_address.interface}", style="dim")
        table.add_row(f"{result.endpoint_short_label} LAN", lan_endpoint_text)
    if result.profile_path is not None:
        table.add_row("Profile", Text(str(result.profile_path)))
    table.add_row("Prompt", Text(str(result.prompt_path)))

    summary_panel = Panel(table, title=title, border_style="green")
    if not lan_exposed:
        return Group(summary_panel)

    warning = Text(f"{result.endpoint_short_label} is exposed to the LAN through a relay. Use this only on a trusted network.", style="yellow")
    return Group(summary_panel, Panel(warning, title="⚠ LAN exposure", border_style="yellow"))


def build_browser_launches_summary(*, results: Sequence[BrowserLaunchResult], lan_address: InterfaceIPv4Address | None) -> Group:
    if len(results) == 0:
        raise ValueError("At least one browser launch result is required")
    lan_exposed = results[0].host == REMOTE_DEBUGGING_LAN
    if any((result.host == REMOTE_DEBUGGING_LAN) != lan_exposed for result in results):
        raise ValueError("Batch browser launch results must use the same LAN exposure mode")
    if lan_exposed != (lan_address is not None):
        raise ValueError("A selected LAN address is required exactly when the browser endpoints are exposed to the LAN")

    table = Table(
        title=f"✓ {results[0].process_label} profiles ready · {len(results)} endpoint(s)", box=box.ROUNDED, header_style="bold cyan", show_lines=False
    )
    table.add_column("Profile", style="bold white")
    table.add_column("IP")
    table.add_column("Port", justify="right", style="bold bright_blue")
    table.add_column("State")
    table.add_column("Runtime", overflow="fold")

    for result in results:
        endpoint_ip = lan_address.ipv4_address if lan_address is not None else result.host
        endpoint = f"http://{endpoint_ip}:{result.port}"
        endpoint_ip_text = Text(endpoint_ip, style="bright_blue")
        endpoint_ip_text.stylize(f"link {endpoint}")
        profile_name = result.profile_path.name if result.profile_path is not None else "-"
        state, runtime = _batch_launch_state(result=result)
        table.add_row(profile_name, endpoint_ip_text, str(result.port), state, runtime)

    if lan_address is None:
        return Group(table)
    interface_details = f"{lan_address.interface} · {lan_address.ipv4_address}"
    warning = Text(
        f"All endpoints are exposed to the LAN through localhost relays on {interface_details}. Use this only on a trusted network.", style="yellow"
    )
    return Group(table, Panel(warning, title="⚠ LAN exposure", border_style="yellow"))


def _batch_launch_state(*, result: BrowserLaunchResult) -> tuple[Text, Text]:
    match result:
        case ExistingBrowserLaunchResult():
            return Text("ready", style="bold green"), Text(f"existing {result.owner} · PID {result.process_id}")
        case DetachedBrowserLaunchResult():
            runtime = f"detached · PID {result.process_id}"
            if result.relay_process_id is not None:
                runtime = f"{runtime} · relay PID {result.relay_process_id}"
            return Text("launched", style="bold green"), Text(runtime)
        case TmuxBrowserLaunchResult():
            return Text("launched", style="bold green"), Text(f"tmux · {result.tmux.browser_window_name}")
