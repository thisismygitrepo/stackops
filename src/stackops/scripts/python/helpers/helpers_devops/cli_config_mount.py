from typing import Annotated, Literal, TypeAlias, TYPE_CHECKING

import typer

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry

if TYPE_CHECKING:
    from rich.table import Table

MountBackend: TypeAlias = Literal["mount", "dislocker", "udisksctl"]


def _display_value(value: str | None) -> str:
    return value if value else "-"


def _build_devices_table(entries: list[DeviceEntry]) -> "Table":
    from rich import box
    from rich.table import Table

    table = Table(title="Available devices for mounting", box=box.SIMPLE_HEAVY, header_style="bold cyan", show_lines=False)
    table.add_column("Device", style="bold white", no_wrap=True)
    table.add_column("Path", style="cyan", no_wrap=True)
    table.add_column("FS", style="green", no_wrap=True)
    table.add_column("Size", style="yellow", justify="right", no_wrap=True)
    table.add_column("Mount", style="blue")
    table.add_column("Label", style="white")
    table.add_column("Details", style="dim", overflow="fold")
    for entry in entries:
        table.add_row(
            entry.key,
            entry.device_path,
            _display_value(entry.fs_type),
            _display_value(entry.size),
            _display_value(entry.mount_point),
            _display_value(entry.label),
            _display_value(entry.extra),
            style="bold" if entry.device_type == "disk" else None,
        )
    return table


def list_devices() -> None:
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices import list_devices as _list_devices

    try:
        entries = _list_devices()
    except RuntimeError as exc:
        typer.echo(f"Device listing failed: {exc}", err=True)
        raise typer.Exit(1)
    if not entries:
        typer.echo("No devices found")
        return
    Console().print(_build_devices_table(entries))


def mount_device(
    device_query: Annotated[str, typer.Argument(...)],
    mount_point: Annotated[str, typer.Argument(...)],
    read_only: bool,
    backend: MountBackend,
) -> None:
    import platform

    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices import list_devices as _list_devices
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.linux import mount_linux, select_linux_partition
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos import mount_macos
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.selection import resolve_device
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.windows import mount_windows

    try:
        entries = _list_devices()
        if not entries:
            typer.echo("No devices found")
            raise typer.Exit(1)
        entry = resolve_device(entries, device_query)
        match platform.system():
            case "Linux":
                mount_linux(select_linux_partition(entries, entry), mount_point, read_only, backend)
            case "Darwin":
                mount_macos(entry, mount_point)
            case "Windows":
                mount_windows(entry, mount_point)
            case unsupported:
                typer.echo(f"Unsupported platform: {unsupported}")
                raise typer.Exit(1)
        typer.echo("Mount completed")
    except RuntimeError as exc:
        typer.echo(f"Mount failed: {exc}")
        raise typer.Exit(1)


def mount_interactive() -> None:
    import platform

    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices import list_devices as _list_devices
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.linux import mount_linux, select_linux_partition
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos import mount_macos
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.selection import pick_device
    from stackops.scripts.python.helpers.helpers_devops.mount_helpers.windows import mount_windows

    try:
        entries = _list_devices()
        if not entries:
            typer.echo("No devices found")
            raise typer.Exit(1)
        entry = pick_device(entries, header="Available devices")
        platform_name = platform.system()
        mount_point = typer.prompt("Mount point (use '-' for default)") if platform_name == "Darwin" else typer.prompt("Mount point")
        read_only = typer.confirm("Mount read-only?", default=False)
        backend_str = typer.prompt("Backend", default="mount", prompt_suffix=" [mount/dislocker/udisksctl]: ")
        if backend_str not in {"mount", "dislocker", "udisksctl"}:
            typer.echo(f"Invalid backend: {backend_str}")
            raise typer.Exit(2)
        backend: MountBackend = backend_str  # type: ignore[assignment]
        match platform_name:
            case "Linux":
                mount_linux(select_linux_partition(entries, entry), mount_point, read_only, backend)
            case "Darwin":
                mount_macos(entry, mount_point)
            case "Windows":
                mount_windows(entry, mount_point)
            case unsupported:
                typer.echo(f"Unsupported platform: {unsupported}")
                raise typer.Exit(1)
        typer.echo("Mount completed")
    except RuntimeError as exc:
        typer.echo(f"Mount failed: {exc}")
        raise typer.Exit(1)
