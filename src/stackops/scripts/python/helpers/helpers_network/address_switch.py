import subprocess
import time

from rich import box
from rich.console import Console
from rich.table import Table

from stackops.utils.network_address import get_public_ip_address


def _ip_is_acceptable(ip: str, current_ip: str | None, target_ip_addresses: list[str] | None) -> bool:
    if target_ip_addresses is not None:
        return ip in target_ip_addresses
    if current_ip and ip != current_ip:
        return True
    if current_ip is None:
        return True
    return False


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")


def _render_command_result(console: Console, result: subprocess.CompletedProcess[str], fallback_success_text: str | None) -> None:
    output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    output_lines.extend(line.strip() for line in result.stderr.splitlines() if line.strip())
    if output_lines:
        for output_line in output_lines:
            console.print(output_line)
        return
    if result.returncode == 0 and fallback_success_text is not None:
        console.print(f"[green]{fallback_success_text}[/green]")
        return
    if result.returncode != 0:
        console.print(f"[red]Command failed with exit code {result.returncode}.[/red]")


def _format_ip_pool(target_ip_addresses: list[str]) -> str:
    return ", ".join(target_ip_addresses)


def _build_ip_rejection_reason(ip: str, current_ip: str | None, target_ip_addresses: list[str] | None) -> str:
    if target_ip_addresses is not None:
        return f"This IP is not acceptable because it's not within this pool: {_format_ip_pool(target_ip_addresses)}."
    if current_ip is None:
        return f"This IP is not acceptable because it could not be validated against the current IP state: {ip}."
    return f"This IP is not acceptable because it matches the current IP: {current_ip}."


def _render_attempted_ips(console: Console, attempted_ips: list[str]) -> None:
    table = Table(title="IPs attempted so far", box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Attempt", justify="right", style="bold")
    table.add_column("IP", style="magenta")
    for attempt_number, attempted_ip in enumerate(attempted_ips, start=1):
        table.add_row(str(attempt_number), attempted_ip)
    console.print(table)


def switch_public_ip_address(max_trials: int, wait_seconds: float, target_ip_addresses: list[str] | None) -> tuple[bool, str]:
    console = Console()
    console.print("[bold cyan]🔁 Switching IP ...[/bold cyan]")
    from stackops.utils.installer_utils.installer_cli import install_if_missing

    install_if_missing(which="warp-cli", binary_name=None, verbose=True)

    current_ip: str | None = None
    try:
        current_data = get_public_ip_address()
        current_ip = current_data.get("ip")
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not get current IP: {e}[/yellow]")

    console.print(f"Current IP: [bold]{current_ip if current_ip is not None else 'unavailable'}[/bold]")
    if target_ip_addresses is not None:
        console.print(f"🎯 Acceptable IP pool: [bold]{_format_ip_pool(target_ip_addresses)}[/bold]")

    if target_ip_addresses is not None and current_ip and current_ip in target_ip_addresses:
        console.print(f"[green]✅ Current IP {current_ip} is already in the acceptable pool. No switch needed.[/green]")
        return True, current_ip

    latest_ip: str = current_ip or ""
    attempted_ips: list[str] = []
    for attempt in range(1, max_trials + 1):
        console.rule(f"[bold cyan]Attempt {attempt}/{max_trials}[/bold cyan]")

        console.print("🔻 Deactivating current connection ...")
        _render_command_result(console, _run_command(["warp-cli", "registration", "delete"]), fallback_success_text=None)

        console.print(f"😴 Sleeping for {wait_seconds:.1f} seconds ...")
        time.sleep(wait_seconds)

        console.print("🔼 Registering new connection ...")
        res_reg = _run_command(["warp-cli", "registration", "new"])
        _render_command_result(console, res_reg, fallback_success_text="Success")
        if res_reg.returncode != 0:
            console.print("[yellow]⚠️ Registration failed, retrying loop...[/yellow]")
            continue

        console.print("🔗 Connecting ...")
        _render_command_result(console, _run_command(["warp-cli", "connect"]), fallback_success_text="Success")

        console.print(f"😴 Sleeping for {wait_seconds:.1f} seconds ...")
        time.sleep(wait_seconds)

        console.print("🔍 Checking status of warp ...")
        _render_command_result(console, _run_command(["warp-cli", "status"]), fallback_success_text=None)

        console.print("🔍 Checking new IP ...")
        new_ip: str | None = None
        for ip_check_attempt in range(1, 6):
            try:
                new_data = get_public_ip_address()
                new_ip = new_data["ip"]
                if new_ip:
                    break
            except Exception as e:
                console.print(f"[yellow]⚠️ Error checking new IP (attempt {ip_check_attempt}/5): {e}[/yellow]")
                time.sleep(wait_seconds)

        latest_ip = new_ip or latest_ip
        if new_ip:
            attempted_ips.append(new_ip)
            console.print(f"New IP: [bold]{new_ip}[/bold]")
            _render_attempted_ips(console, attempted_ips)
            if _ip_is_acceptable(new_ip, current_ip, target_ip_addresses):
                console.print("[green]✅ Done ... IP switched successfully.[/green]")
                return True, new_ip
            console.print(f"[bold yellow]❌ {_build_ip_rejection_reason(new_ip, current_ip, target_ip_addresses)}[/bold yellow]")
            console.print("[yellow]Retrying...[/yellow]")
        else:
            console.print("[yellow]⚠️ Could not retrieve new IP after multiple attempts.[/yellow]")

    console.print("[bold red]❌ Failed to switch IP after max trials.[/bold red]")
    return False, latest_ip

if __name__ == "__main__":
    switch_public_ip_address(max_trials=10, wait_seconds=4.0, target_ip_addresses=None)
