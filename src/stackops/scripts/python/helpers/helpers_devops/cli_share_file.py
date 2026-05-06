
import typer
from typing import Annotated, Literal


def _quote_powershell_argument(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"""'{escaped_value}'"""


def share_file_receive(code_args: Annotated[list[str], typer.Argument(help="Receive code or relay command. Examples: '7121-donor-olympic-bicycle' or '--relay 10.17.62.206:443 7121-donor-olympic-bicycle'")],
    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,
    ) -> None:
    """Receive a file using croc with relay server.
Usage examples:
    devops network receive 7121-donor-olympic-bicycle
    devops network receive -- --relay 10.17.62.206:443 7121-donor-olympic-bicycle
    devops network receive -- croc --relay 10.17.62.206:443 7121-donor-olympic-bicycle
"""
    if install_missing_dependencies:
        from stackops.utils.installer_utils.installer_cli import install_if_missing
        install_if_missing(which="croc", binary_name=None, verbose=True)
    import platform
    import shlex
    import sys

    is_windows = platform.system() == "Windows"

    # If no args passed via typer, try to get them from sys.argv directly
    # This handles the case where -- was used and arguments weren't parsed by typer
    if not code_args or (len(code_args) == 1 and code_args[0] in ['--relay', 'croc']):
        # Find the index of 'rx' or 'receive' in sys.argv and get everything after it
        try:
            for i, arg in enumerate(sys.argv):
                if arg in ['rx', 'receive', 'r'] and i + 1 < len(sys.argv):
                    code_args = sys.argv[i + 1:]
                    break
        except Exception:
            pass

    input_str = " ".join(code_args)
    try:
        tokens = shlex.split(input_str)
    except ValueError as exc:
        typer.echo(f"❌ Error: Could not parse croc receive code from input: {input_str}", err=True)
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    relay_server: str | None = None
    secret_code: str | None = None

    tokens = [token for token in tokens if token not in ["--", "croc", "export"]]

    relay_indexes: set[int] = set()
    for i, token in enumerate(tokens):
        if token == "--relay":
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("-"):
                typer.echo("❌ Error: --relay requires a relay server.", err=True)
                raise typer.Exit(code=1)
            relay_server = tokens[i + 1]
            relay_indexes = {i, i + 1}
            break

    for token in tokens:
        if token.startswith("CROC_SECRET="):
            secret_code = token.split("=", 1)[1].strip('"').strip("'")
            break

    if not secret_code:
        for i, token in enumerate(tokens):
            if i not in relay_indexes and not token.startswith("-") and not token.startswith("CROC_SECRET="):
                secret_code = token
                break

    if not secret_code:
        typer.echo(f"❌ Error: Could not parse croc receive code from input: {input_str}", err=True)
        typer.echo("Usage:", err=True)
        typer.echo("  devops network receive 7121-donor-olympic-bicycle", err=True)
        typer.echo("  devops network receive -- --relay 10.17.62.206:443 7121-donor-olympic-bicycle", err=True)
        raise typer.Exit(code=1)

    # Build the appropriate script for current OS
    if is_windows:
        # Windows PowerShell format: croc --relay server:port secret-code --yes
        relay_arg = f"--relay {_quote_powershell_argument(relay_server)}" if relay_server else ""
        code_arg = _quote_powershell_argument(secret_code)
        script = f"""croc {relay_arg} {code_arg} --yes""".strip()
    else:
        # Linux/macOS Bash format: CROC_SECRET="secret-code" croc --relay server:port --yes
        relay_arg = f"--relay {shlex.quote(relay_server)}" if relay_server else ""
        script = f"""export CROC_SECRET={shlex.quote(secret_code)}
croc {relay_arg} --yes""".strip()

    from stackops.utils.code import exit_then_run_shell_script, print_code
    print_code(code=script, desc="🚀 Receiving file with croc", lexer="powershell" if is_windows else "bash")
    exit_then_run_shell_script(script=script, strict=False)


def share_file_send(path: Annotated[str | None, typer.Argument(help="Path to the file or directory to send. Required unless --text is provided.")] = None,
                    zip_folder: Annotated[bool, typer.Option("--zip", help="Zip folder before sending")] = False,
                    code: Annotated[str | None, typer.Option("--code", "-c", help="Codephrase used to connect to relay")] = None,
                    text: Annotated[str | None, typer.Option("--text", "-t", help="Send some text")] = None,
                    qrcode: Annotated[bool, typer.Option("--qrcode", "--qr", help="Show receive code as a qrcode")] = False,
                    backend: Annotated[Literal["wormhole", "w", "croc", "c"], typer.Option("--backend", "-b", help="Backend to use")] = "croc",
                    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,
                    ) -> None:
    """Send a file, directory, or text."""
    import platform
    import shlex

    if text is None and path is None:
        typer.echo("❌ Error: Provide a path or --text.", err=True)
        raise typer.Exit(code=1)
    if text is not None and path is not None:
        typer.echo("❌ Error: Provide either a path or --text, not both.", err=True)
        raise typer.Exit(code=1)
    if text is not None and zip_folder:
        typer.echo("❌ Error: --zip can only be used when sending a file or directory.", err=True)
        raise typer.Exit(code=1)
    if qrcode and backend in ("wormhole", "w"):
        typer.echo("❌ Error: --qrcode is only supported with the croc backend.", err=True)
        raise typer.Exit(code=1)

    is_windows = platform.system() == "Windows"
    send_target = "text" if text is not None else path
    receive_hint: str
    print_desc: str

    def quote_shell_arg(value: str) -> str:
        if is_windows:
            return _quote_powershell_argument(value)
        return shlex.quote(value)

    match backend:
        case "wormhole" | "w":
            command_parts = ["uvx", "--from", "magic-wormhole", "wormhole", "send"]
            if code is not None:
                command_parts.extend(["--code", quote_shell_arg(code)])
            if text is not None:
                command_parts.extend(["--text", quote_shell_arg(text)])
            elif path is not None:
                command_parts.append(quote_shell_arg(path))
            script = " ".join(command_parts)
            receive_hint = "uvx --from magic-wormhole wormhole receive"
            print_desc = "🚀 sending file with magic-wormhole"
        case "croc" | "c":
            if install_missing_dependencies:
                from stackops.utils.installer_utils.installer_cli import install_if_missing
                install_if_missing(which="croc", binary_name=None, verbose=True)

            # Get relay server IP from environment or use default
            import stackops.scripts.python.helpers.helpers_network.address as helper
            res = helper.select_lan_ipv4(prefer_vpn=False)
            if res is None:
                typer.echo("❌ Error: Could not determine local LAN IPv4 address for relay.", err=True)
                raise typer.Exit(code=1)
            local_ip_v4 = res
            relay_port = "443"
            relay_endpoint = f"{local_ip_v4}:{relay_port}"
            command_parts = ["croc", "--relay", relay_endpoint, "--ip", relay_endpoint, "send"]
            if is_windows and code is not None:
                command_parts.extend(["--code", quote_shell_arg(code)])
            if zip_folder:
                command_parts.append("--zip")
            if qrcode:
                command_parts.append("--qrcode")
            if text is not None:
                command_parts.extend(["--text", quote_shell_arg(text)])
            elif path is not None:
                command_parts.append(quote_shell_arg(path))

            if is_windows:
                # Windows PowerShell format
                script = " ".join(command_parts)
            else:
                # Linux/macOS Bash format
                croc_command = " ".join(command_parts)
                if code is not None:
                    script = f"""export CROC_SECRET={shlex.quote(code)}
{croc_command}"""
                else:
                    script = croc_command
            receive_hint = "devops network receive"
            print_desc = "🚀 sending file with croc"

    typer.echo(f"🚀 Sending {send_target}. Use: {receive_hint}")
    from stackops.utils.code import exit_then_run_shell_script, print_code
    print_code(code=script, desc=print_desc, lexer="powershell" if is_windows else "bash")
    exit_then_run_shell_script(script=script, strict=False)
