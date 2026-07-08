from typing import Annotated

import typer


def cloudflare_tunnel_status(
    tunnel_name: Annotated[str, typer.Argument(..., help="Named Cloudflare tunnel to inspect")],
    hosts: Annotated[list[str] | None, typer.Option("--host", "-H", help="SSH connector host; repeat for multiple hosts")] = None,
    hostnames: Annotated[list[str] | None, typer.Option("--hostname", "-n", help="Published hostname to check on each connector")] = None,
    include_local: Annotated[bool, typer.Option("--local/--no-local", help="Inspect the local connector service and routes")] = True,
    cloudflared_binary: Annotated[
        str, typer.Option("--cloudflared", help="cloudflared executable path on every connector")
    ] = "~/.local/bin/cloudflared",
    config_path: Annotated[str, typer.Option("--config", help="cloudflared configuration path on every connector")] = "/etc/cloudflared/config.yml",
    service_name: Annotated[str, typer.Option("--service", help="systemd service name on every connector")] = "cloudflared",
) -> None:
    """☁ <t> Show tunnel redundancy, versions, services, and route coverage."""
    from rich.console import Console
    from rich.table import Table

    from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_runtime import get_tunnel_health, inspect_connector_host

    console = Console()
    try:
        health = get_tunnel_health(tunnel_name=tunnel_name, cloudflared_binary=cloudflared_binary)
        targets: list[str | None] = [None] if include_local else []
        targets.extend(hosts or [])
        statuses = [
            inspect_connector_host(
                host=target,
                hostnames=tuple(hostnames or []),
                cloudflared_binary=cloudflared_binary,
                config_path=config_path,
                service_name=service_name,
            )
            for target in targets
        ]
    except (OSError, RuntimeError, ValueError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    expected_edge_sessions = health.connector_count * 4
    versions = ", ".join(f"{version} × {count}" for version, count in health.versions)
    console.print(
        f"[bold]Tunnel {tunnel_name}:[/bold] {health.connector_count} connectors, "
        f"{health.edge_session_count}/{expected_edge_sessions} edge sessions, versions: {versions or '-'}"
    )

    table = Table(title="Cloudflare Tunnel Connectors")
    table.add_column("Host")
    table.add_column("Service")
    table.add_column("Version")
    table.add_column("Config")
    table.add_column("Routes")
    for status in statuses:
        routes = ", ".join(f"{hostname}={'yes' if covered else 'no'}" for hostname, covered in status.route_coverage) or "-"
        table.add_row(
            status.host, "active" if status.service_active else "inactive", status.version, "valid" if status.config_valid else "invalid", routes
        )
    if statuses:
        console.print(table)


def update_cloudflare_connectors(
    hosts: Annotated[list[str] | None, typer.Option("--host", "-H", help="SSH connector host; repeat for rolling updates")] = None,
    include_local: Annotated[bool, typer.Option("--local/--no-local", help="Include the local connector in the rolling update")] = True,
    cloudflared_binary: Annotated[
        str, typer.Option("--cloudflared", help="cloudflared executable path on every connector")
    ] = "~/.local/bin/cloudflared",
    service_name: Annotated[str, typer.Option("--service", help="systemd service name on every connector")] = "cloudflared",
    timeout_seconds: Annotated[int, typer.Option("--timeout", min=1, help="Seconds to wait for each restarted service")] = 60,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Run without confirmation")] = False,
) -> None:
    """⬆ <u> Rolling-update local and SSH Cloudflare Tunnel connectors."""
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_maintenance import rolling_update_connectors

    targets = (["local"] if include_local else []) + list(hosts or [])
    if len(targets) == 0:
        raise typer.BadParameter("Select --local or provide at least one --host.")
    if not yes and not typer.confirm(f"Update connectors sequentially on: {', '.join(targets)}?", default=False):
        raise typer.Abort()

    try:
        rolling_update_connectors(
            hosts=tuple(hosts or []),
            include_local=include_local,
            cloudflared_binary=cloudflared_binary,
            service_name=service_name,
            timeout_seconds=timeout_seconds,
        )
    except (OSError, RuntimeError, ValueError) as error:
        Console().print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error


def sync_cloudflare_routes(
    hostnames: Annotated[list[str], typer.Option(..., "--hostname", "-n", help="Source hostname route to copy; repeat as needed")],
    source_host: Annotated[str | None, typer.Option("--source-host", help="SSH host containing the source configuration")] = None,
    source_config: Annotated[str, typer.Option("--source-config", help="Source cloudflared configuration path")] = "/etc/cloudflared/config.yml",
    target_host: Annotated[str | None, typer.Option("--host", "-H", help="SSH target host; omit for the local machine")] = None,
    target_config: Annotated[str, typer.Option("--config", help="Target cloudflared configuration path")] = "/etc/cloudflared/config.yml",
    cloudflared_binary: Annotated[str, typer.Option("--cloudflared", help="cloudflared executable path on the target")] = "~/.local/bin/cloudflared",
    service_name: Annotated[str, typer.Option("--service", help="Target systemd service name")] = "cloudflared",
    timeout_seconds: Annotated[int, typer.Option("--timeout", min=1, help="Seconds to wait for the restarted service")] = 60,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Run without confirmation")] = False,
) -> None:
    """🔀 <y> Copy selected ingress routes without copying tunnel credentials."""
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_devops.cloudflare_tunnel_maintenance import sync_ingress_routes

    target_label = target_host or "local"
    if not yes and not typer.confirm(f"Merge {len(hostnames)} route(s) into {target_label} and restart {service_name}?", default=False):
        raise typer.Abort()
    try:
        sync_ingress_routes(
            source_host=source_host,
            source_config=source_config,
            target_host=target_host,
            target_config=target_config,
            hostnames=tuple(hostnames),
            cloudflared_binary=cloudflared_binary,
            service_name=service_name,
            timeout_seconds=timeout_seconds,
        )
    except (OSError, RuntimeError, ValueError) as error:
        Console().print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error


def register_commands(device_app: typer.Typer) -> None:
    device_app.command(name="cloudflare-tunnel-status", help="☁ <t> Show tunnel redundancy, versions, services, and routes")(cloudflare_tunnel_status)
    device_app.command(name="t", help="Show Cloudflare Tunnel status", hidden=True)(cloudflare_tunnel_status)
    device_app.command(name="update-cloudflare-connectors", help="⬆ <u> Rolling-update Cloudflare Tunnel connectors")(update_cloudflare_connectors)
    device_app.command(name="u", help="Rolling-update Cloudflare Tunnel connectors", hidden=True)(update_cloudflare_connectors)
    device_app.command(name="sync-cloudflare-routes", help="🔀 <y> Copy selected ingress routes without tunnel credentials")(sync_cloudflare_routes)
    device_app.command(name="y", help="Copy selected Cloudflare Tunnel ingress routes", hidden=True)(sync_cloudflare_routes)
