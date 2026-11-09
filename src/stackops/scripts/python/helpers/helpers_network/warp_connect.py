import json
import platform
import subprocess
import time
from dataclasses import dataclass
from typing import Literal, TypeAlias

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from stackops.scripts.python.helpers.helpers_network.warp_status import WarpStatus, describe_warp_status, read_warp_status, request_warp_action
from stackops.utils.cli_utils.interaction import is_interactive
from stackops.utils.installer_utils.installer_cli import install_clis, install_if_missing
from stackops.utils.network.address import PublicIpInfo, get_public_ip_address
from stackops.utils.schemas.installer.installer_types import InstallRequest

WARP_FAILURE_REASON: TypeAlias = Literal["install_failed", "update_failed", "daemon_unavailable", "registration_failed", "connect_rejected", "connection_timeout"]


@dataclass(frozen=True, slots=True)
class WarpConnected:
    status: WarpStatus


@dataclass(frozen=True, slots=True)
class WarpFailure:
    reason: WARP_FAILURE_REASON
    message: str


@dataclass(frozen=True, slots=True)
class WarpSnapshot:
    status: WarpStatus
    public_ip: PublicIpInfo | None


def _read_public_ip(retry_seconds: float, wait_seconds: float) -> PublicIpInfo | None:
    deadline = time.monotonic() + retry_seconds
    while True:
        try:
            return get_public_ip_address()
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            if time.monotonic() >= deadline:
                return None
            time.sleep(wait_seconds)


def _update_warp_cli() -> WarpFailure | None:
    results = install_clis(
        clis_names=["warp-cli"], install_request=InstallRequest(version=None, update=True, user_scripts_root=None), source="library", user_path=None
    )
    if any(result["kind"] == "failed" for result in results):
        return WarpFailure(reason="update_failed", message="Could not update warp-cli, see the installation results above.")
    return None


def _start_daemon(console: Console) -> WarpFailure | None:
    system = platform.system()
    if system != "Linux":
        return WarpFailure(reason="daemon_unavailable", message=f"""Start the Cloudflare WARP service manually, it is not running on {system}.""")
    console.print("🛠  Starting the warp-svc service ...")
    sudo = ["sudo"] if is_interactive() else ["sudo", "-n"]
    if subprocess.run([*sudo, "systemctl", "start", "warp-svc"], check=False).returncode != 0:
        return WarpFailure(reason="daemon_unavailable", message="Could not start the warp-svc service.")
    return None


def _register_device(wait_seconds: float, console: Console) -> WarpFailure | None:
    console.print("📝 Registering this device with WARP ...")
    rejection = request_warp_action(("registration", "new"))
    if rejection is None:
        return None
    if rejection.code != "RegistrationExists":
        return WarpFailure(reason="registration_failed", message=f"""WARP registration failed: {rejection.message}""")
    time.sleep(wait_seconds)
    if read_warp_status().state != "registration_missing":
        return None
    console.print("♻️  Replacing the stale WARP registration ...")
    rejection = request_warp_action(("registration", "delete")) or request_warp_action(("registration", "new"))
    return None if rejection is None else WarpFailure(reason="registration_failed", message=f"""WARP re-registration failed: {rejection.message}""")


def _drive_to_connected(timeout_seconds: float, wait_seconds: float, console: Console) -> WarpConnected | WarpFailure:
    deadline = time.monotonic() + timeout_seconds
    previous: WarpStatus | None = None
    daemon_start_attempted = False
    registration_attempted = False
    while True:
        status = read_warp_status()
        if status != previous:
            console.print(f"""   ↳ {escape(describe_warp_status(status))}""")
        match status.state:
            case "connected":
                return WarpConnected(status=status)
            case "daemon_down":
                failure = None if daemon_start_attempted else _start_daemon(console=console)
                daemon_start_attempted = True
                if failure is not None:
                    return failure
            case "registration_missing":
                failure = None if registration_attempted else _register_device(wait_seconds=wait_seconds, console=console)
                registration_attempted = True
                if failure is not None:
                    return failure
            case "disconnected" | "unable":
                if status != previous:
                    console.print("🔗 Requesting a WARP connection ...")
                    rejection = request_warp_action(("connect",))
                    if rejection is not None:
                        return WarpFailure(reason="connect_rejected", message=f"""warp-cli refused to connect: {rejection.message}""")
            case "connecting":
                pass
        previous = status
        if time.monotonic() >= deadline:
            return WarpFailure(reason="connection_timeout", message=f"""WARP did not connect within {timeout_seconds:g}s: {describe_warp_status(status)}""")
        time.sleep(wait_seconds)


def _render_comparison(console: Console, before: WarpSnapshot, after: WarpSnapshot) -> None:
    table = Table(title="🌐 Cloudflare WARP", header_style="bold cyan")
    table.add_column("")
    table.add_column("Before")
    table.add_column("After", style="bold")
    table.add_row("Status", escape(describe_warp_status(before.status)), escape(describe_warp_status(after.status)))
    for label, describe in (
        ("Public IP", lambda info: info["ip"]),
        ("Location", lambda info: f"""{info.get("city", "?")}, {info.get("country_name", "?")}"""),
        ("Network", lambda info: info.get("org", "?")),
    ):
        table.add_row(label, *("unavailable" if snapshot.public_ip is None else escape(describe(snapshot.public_ip)) for snapshot in (before, after)))
    console.print(table)


def connect_warp(update: bool, timeout_seconds: float, wait_seconds: float) -> WarpConnected | WarpFailure:
    console = Console()
    if not install_if_missing(which="warp-cli", binary_name=None, verbose=False):
        failure = WarpFailure(reason="install_failed", message="warp-cli is not installed and could not be installed automatically.")
        console.print(f"""[bold red]❌ {escape(failure.message)}[/bold red]""")
        return failure
    before = WarpSnapshot(status=read_warp_status(), public_ip=_read_public_ip(retry_seconds=0.0, wait_seconds=wait_seconds))
    console.print(f"""🔍 Public IP before connecting: {before.public_ip["ip"] if before.public_ip else "unavailable"}""")
    outcome = _update_warp_cli() if update else None
    if outcome is None:
        outcome = _drive_to_connected(timeout_seconds=timeout_seconds, wait_seconds=wait_seconds, console=console)
    ip_retry_seconds = timeout_seconds if isinstance(outcome, WarpConnected) else 0.0
    after = WarpSnapshot(status=read_warp_status(), public_ip=_read_public_ip(retry_seconds=ip_retry_seconds, wait_seconds=wait_seconds))
    _render_comparison(console=console, before=before, after=after)
    match outcome:
        case WarpConnected():
            console.print("[bold green]✅ WARP is connected.[/bold green]")
        case WarpFailure():
            console.print(f"""[bold red]❌ {escape(outcome.message)}[/bold red]""")
    return outcome
