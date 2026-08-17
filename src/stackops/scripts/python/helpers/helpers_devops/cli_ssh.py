import subprocess
from typing import Annotated

import typer

from stackops.utils.installer_utils.linux_package_manager import detect_current_linux_distribution
from stackops.utils.ssh_utils.server_install import (
    build_linux_ssh_server_install_script as _get_linux_ssh_server_install_script,
    build_macos_ssh_server_install_script as _get_macos_ssh_server_install_script,
)
from stackops.utils.ssh_utils.windows_server_install import (
    build_windows_ssh_server_install_script as _get_windows_ssh_server_install_script,
)


def _run_add_ssh_key_with_paramiko(pub_path: str | None, pub_choose: bool, pub_val: bool, from_github: str | None, remote: str) -> None:
    import stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key as helper

    helper.main(pub_path=pub_path, pub_choose=pub_choose, pub_val=pub_val, from_github=from_github, remote=remote)


def install_ssh_server() -> None:
    """📡 Install SSH server"""
    import platform

    system = platform.system()
    if system == "Windows":
        script = _get_windows_ssh_server_install_script()
        from stackops.utils.code import run_shell_script

        result = run_shell_script(script=script, display_script=True, clean_env=False)
    elif system == "Linux":
        distribution = detect_current_linux_distribution()
        print(f"🐧 Installing OpenSSH server on {distribution.distribution_id} using {distribution.package_manager}.")
        script = _get_linux_ssh_server_install_script(distribution)
        result = subprocess.run(("/bin/sh", "-s"), input=script, text=True, check=False)
    elif system == "Darwin":
        script = _get_macos_ssh_server_install_script()
        result = subprocess.run(("/bin/sh", "-s"), input=script, text=True, check=False)
    else:
        print(f"❌ Error: Platform {system} is not supported.")
        raise typer.Exit(code=1)
    if result.returncode != 0:
        raise RuntimeError(f"SSH server installation failed with exit code {result.returncode}")


def change_ssh_port(port: Annotated[int, typer.Option("--port", "-p", help="SSH port to use", min=1, max=65535)] = 2222) -> None:
    """🔌 Change SSH port (Linux/WSL only, default: 2222)"""
    import platform

    if platform.system() != "Linux":
        print("❌ Error: change_ssh_port requires Linux environment")
        raise typer.Exit(code=1)
    from stackops.utils.ssh_utils.wsl import change_ssh_port as _change_ssh_port

    _change_ssh_port(port=port)


def add_ssh_key(
    path: Annotated[str | None, typer.Option(..., "--path", "-p", help="Path to the public key file")] = None,
    choose: Annotated[bool, typer.Option(..., "--choose", "-c", help="Choose from available public keys in ~/.ssh/*.pub")] = False,
    value: Annotated[bool, typer.Option(..., "--value", "-v", help="Paste the public key content manually")] = False,
    github: Annotated[str | None, typer.Option(..., "--github", "-g", help="Fetch public keys from a GitHub username")] = None,
    remote: Annotated[str | None, typer.Option(..., "--remote", "-r", help="Deploy to remote machine (config-name or user@host:port)")] = None,
) -> None:
    """🔑 Add SSH public key to this machine (or remote with --remote)."""
    source_count = sum([path is not None, choose, value, github is not None])
    if source_count != 1:
        print("❌ Error: choose exactly one key source: --path, --choose, --value, or --github.")
        import sys

        sys.exit(1)

    if remote is not None:
        from stackops.utils.code import run_lambda_function
        from stackops.utils.optional_dependencies import PARAMIKO_UV_WITH

        proc = run_lambda_function(
            lambda: _run_add_ssh_key_with_paramiko(pub_path=path, pub_choose=choose, pub_val=value, from_github=github, remote=remote),
            uv_with=list(PARAMIKO_UV_WITH),
            uv_project_dir=None,
        )
        if proc.returncode != 0:
            raise typer.Exit(code=proc.returncode)
        return

    import stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key as helper

    helper.main(pub_path=path, pub_choose=choose, pub_val=value, from_github=github, remote=remote)


def debug_ssh(
    client_host: Annotated[str | None, typer.Option("--client-host", help="Resolved SSH client host name for Match rules")] = None,
    client_address: Annotated[str | None, typer.Option("--client-address", help="SSH client source IP address for Match rules")] = None,
    local_address: Annotated[str | None, typer.Option("--local-address", help="Server local IP address receiving the connection")] = None,
    local_port: Annotated[int | None, typer.Option("--local-port", help="Server local TCP port receiving the connection", min=1, max=65535)] = None,
    routing_domain: Annotated[str | None, typer.Option("--routing-domain", help="Optional routing domain for Match RDomain rules")] = None,
) -> None:
    """🐛 Debug SSH connection"""
    from platform import system

    from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import SSHDConnectionContext

    supplied_context = (client_host, client_address, local_address, local_port)
    if all(value is None for value in supplied_context) and routing_domain is None:
        connection_context = None
    elif (
        isinstance(client_host, str)
        and isinstance(client_address, str)
        and isinstance(local_address, str)
        and isinstance(local_port, int)
    ):
        connection_context = SSHDConnectionContext(
            client_host_name=client_host,
            client_address=client_address,
            local_address=local_address,
            local_port=local_port,
            routing_domain=routing_domain,
        )
    else:
        print("❌ Error: --client-host, --client-address, --local-address, and --local-port must be supplied together.")
        raise typer.Exit(code=2)

    current_system = system()
    if current_system == "Linux":
        import stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux as ssh_debug_linux

        result = ssh_debug_linux.ssh_debug_linux(connection_context=connection_context)
    elif current_system == "Darwin":
        from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin import ssh_debug_darwin

        result = ssh_debug_darwin(connection_context=connection_context)
    elif current_system == "Windows":
        from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows import ssh_debug_windows

        result = ssh_debug_windows(connection_context=connection_context)
    else:
        print(f"❌ Error: Platform {current_system} is not supported.")
        raise typer.Exit(code=1)
    if not result.summary.ready:
        raise typer.Exit(code=1)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops import cli_ssh_port

    ssh_app = typer.Typer(help="🔐 SSH subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    ssh_app.command(name="install-server", help="📡 <i> Install SSH server")(install_ssh_server)
    ssh_app.command(name="i", help="Install SSH server", hidden=True)(install_ssh_server)
    ssh_app.command(name="change-port", help="🔌 <p> Change SSH port (Linux/WSL only)")(change_ssh_port)
    ssh_app.command(name="p", help="Change SSH port", hidden=True)(change_ssh_port)
    ssh_app.command(name="add-key", help="🔑 <k> Add SSH public key to this machine", no_args_is_help=True)(add_ssh_key)
    ssh_app.command(name="k", help="Add SSH public key to this machine", hidden=True, no_args_is_help=True)(add_ssh_key)

    ssh_app.command(name="debug", help="🐛 <d> Debug SSH connection")(debug_ssh)
    ssh_app.command(name="d", help="Debug SSH connection", hidden=True)(debug_ssh)
    ssh_app.command(name="map-port", help="🔀 <m> Map a remote TCP port to local loopback over SSH", no_args_is_help=True)(cli_ssh_port.map_port)
    ssh_app.command(name="m", help="Map a remote TCP port to local loopback over SSH", hidden=True, no_args_is_help=True)(cli_ssh_port.map_port)
    return ssh_app
