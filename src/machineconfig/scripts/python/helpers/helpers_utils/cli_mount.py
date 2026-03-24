from typing import Annotated

import typer


def list_devices() -> None:
    from machineconfig.scripts.python.helpers.helpers_devops import cli_config_mount

    cli_config_mount.list_devices()


def mount_device(
    device_query: Annotated[str | None, typer.Option("--device", "-d", help="Device query (path, key, or label).")] = None,
    mount_point: Annotated[str | None, typer.Option("--mount-point", "-p", help="Mount point (use '-' for default on macOS).")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Pick device and mount point interactively.")] = False,
) -> None:
    from machineconfig.scripts.python.helpers.helpers_devops import cli_config_mount

    if interactive:
        cli_config_mount.mount_interactive()
        return
    if device_query is None or mount_point is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + "--device and --mount-point are required unless --interactive is set"
        typer.echo(msg)
        raise typer.Exit(2)
    cli_config_mount.mount_device(device_query=device_query, mount_point=mount_point)


def register_mount_commands(app: typer.Typer) -> None:
    app.command("list-devices", no_args_is_help=False, help="💽 <l> List available devices for mounting.")(list_devices)
    app.command("l", no_args_is_help=False, help="List available devices for mounting.", hidden=True)(list_devices)
    app.command("mount", no_args_is_help=True, help="🔌 <m> Mount a device to a mount point.")(mount_device)
    app.command("m", no_args_is_help=True, help="Mount a device to a mount point.", hidden=True)(mount_device)
