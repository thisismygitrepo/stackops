
import platform
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.devices import list_devices as list_devices_internal
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.linux import mount_linux, select_linux_partition
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.macos import mount_macos
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.selection import pick_device, resolve_device
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.windows import mount_windows


console = Console()


def _display_value(value: str | None) -> str:
	if value is None or value == "":
		return "-"
	return value


def _build_devices_table(entries: list[DeviceEntry]) -> Table:
	table = Table(
		title="Available devices for mounting",
		box=box.SIMPLE_HEAVY,
		header_style="bold cyan",
		show_lines=False,
	)
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
	entries = list_devices_internal()
	if not entries:
		typer.echo("No devices found")
		return
	console.print(_build_devices_table(entries))


def mount_device(
	device_query: Annotated[str, typer.Argument(...)],
	mount_point: Annotated[str, typer.Argument(...)],
) -> None:
	try:
		entries = list_devices_internal()
		if not entries:
			typer.echo("No devices found")
			raise typer.Exit(1)
		entry = resolve_device(entries, device_query)
		platform_name = platform.system()
		if platform_name == "Linux":
			selected = select_linux_partition(entries, entry)
			mount_linux(selected, mount_point)
		elif platform_name == "Darwin":
			mount_macos(entry, mount_point)
		elif platform_name == "Windows":
			mount_windows(entry, mount_point)
		else:
			typer.echo(f"Unsupported platform: {platform_name}")
			raise typer.Exit(1)
		typer.echo("Mount completed")
	except RuntimeError as exc:
		typer.echo(f"Mount failed: {exc}")
		raise typer.Exit(1)


def mount_interactive() -> None:
	try:
		entries = list_devices_internal()
		if not entries:
			typer.echo("No devices found")
			raise typer.Exit(1)
		entry = pick_device(entries, header="Available devices")
		platform_name = platform.system()
		if platform_name == "Darwin":
			mount_point = typer.prompt("Mount point (use '-' for default)")
		else:
			mount_point = typer.prompt("Mount point")
		if platform_name == "Linux":
			selected = select_linux_partition(entries, entry)
			mount_linux(selected, mount_point)
		elif platform_name == "Darwin":
			mount_macos(entry, mount_point)
		elif platform_name == "Windows":
			mount_windows(entry, mount_point)
		else:
			typer.echo(f"Unsupported platform: {platform_name}")
			raise typer.Exit(1)
		typer.echo("Mount completed")
	except RuntimeError as exc:
		typer.echo(f"Mount failed: {exc}")
		raise typer.Exit(1)
