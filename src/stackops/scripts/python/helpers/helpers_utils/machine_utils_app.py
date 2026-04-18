from typing import Annotated, Literal, TypeAlias

import typer


ProcessSearchField: TypeAlias = Literal[
    "command",
    "c",
    "ports",
    "p",
    "name",
    "n",
    "pid",
    "P",
    "username",
    "u",
    "status",
    "s",
    "memory",
    "m",
    "cpu",
    "C",
]
EnvironmentSelector: TypeAlias = Literal["PATH", "p", "ENV", "e"]
MountBackendOption: TypeAlias = Literal["mount", "dislocker", "udisksctl"]


def kill_process(
    interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Interactively choose the process to kill")] = True,
    search_by: Annotated[
        ProcessSearchField,
        typer.Option(..., "--filter-by", "-f", help="Field used to search/filter processes in interactive mode."),
    ] = "command",
) -> None:
    from stackops.utils.procs import ProcessManager

    if interactive:
        proc = ProcessManager()
        match search_by:
            case "command" | "c":
                search_field = "command"
            case "ports" | "p":
                search_field = "ports"
            case "name" | "n":
                search_field = "name"
            case "pid" | "P":
                search_field = "pid"
            case "username" | "u":
                search_field = "username"
            case "status" | "s":
                search_field = "status"
            case "memory" | "m":
                search_field = "memory"
            case "cpu" | "C":
                search_field = "cpu"
            case _:
                typer.echo(f"Invalid search_by value: {search_by}", err=True)
                raise typer.Exit(code=1)
        proc.choose_and_kill(search_by=search_field)
        return

    _ = ProcessManager


def tui_env(
    which: Annotated[EnvironmentSelector, typer.Argument(help="Which environment variable to display.")] = "ENV",
    tui: Annotated[bool, typer.Option("--tui", "-t", help="Use the full-screen Textual TUI instead of the default fuzzy picker.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.python import tui_env as impl

    impl(which=which, tui=tui)


def get_machine_specs(
    hardware: Annotated[bool, typer.Option(..., "--hardware", "-h", help="Show compute capability")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.python import get_machine_specs as impl

    impl(hardware=hardware)


def list_devices() -> None:
    from stackops.scripts.python.helpers.helpers_devops import cli_config_mount

    cli_config_mount.list_devices()


def mount_device(
    device_query: Annotated[str | None, typer.Option("--device", "-d", help="Device query (path, key, or label).")] = None,
    mount_point: Annotated[str | None, typer.Option("--mount-point", "-p", help="Mount point (use '-' for default on macOS).")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Pick device and mount point interactively.")] = False,
    read_only: Annotated[bool, typer.Option("--read-only", "-r", help="Mount in read-only mode.")] = False,
    backend: Annotated[
        MountBackendOption,
        typer.Option("--backend", "-b", help="Mount backend: mount | dislocker | udisksctl."),
    ] = "mount",
) -> None:
    from stackops.scripts.python.helpers.helpers_devops import cli_config_mount

    if interactive:
        cli_config_mount.mount_interactive()
        return
    if device_query is None or mount_point is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + "--device and --mount-point are required unless --interactive is set"
        typer.echo(msg)
        raise typer.Exit(2)

    cli_config_mount.mount_device(device_query=device_query, mount_point=mount_point, read_only=read_only, backend=backend)


def get_app() -> typer.Typer:
    machine_app = typer.Typer(help="🖥 <m> Machine and device utilities", no_args_is_help=True, add_help_option=True, add_completion=False)
    machine_app.command(name="kill-process", no_args_is_help=False, help="⚔ <k> Choose a process to kill")(kill_process)
    machine_app.command(name="k", no_args_is_help=False, hidden=True)(kill_process)
    machine_app.command(
        name="environment",
        no_args_is_help=False,
        help="⌘ <v> Navigate ENV/PATH variables. Default: fuzzy picker with preview; use --tui for Textual.",
    )(tui_env)
    machine_app.command(name="v", no_args_is_help=False, hidden=True)(tui_env)
    machine_app.command(name="get-machine-specs", no_args_is_help=False, help="🖥 <g> Get machine specifications.")(get_machine_specs)
    machine_app.command(name="g", no_args_is_help=False, hidden=True)(get_machine_specs)
    machine_app.command(name="list-devices", no_args_is_help=False, help="💽 <l> List available devices for mounting.")(list_devices)
    machine_app.command(name="l", no_args_is_help=False, hidden=True)(list_devices)
    machine_app.command(name="mount", no_args_is_help=True, help="🔌 <m> Mount a device to a mount point.")(mount_device)
    machine_app.command(name="m", no_args_is_help=True, hidden=True)(mount_device)
    return machine_app
