
import typer
from typing import Annotated, Literal

from stackops.utils.cloud.encryption import EncryptionModeChoice
from stackops.utils.constants import IS_REPO_DEVELOPER


def _quote_powershell_argument(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"""'{escaped_value}'"""


def share_file_receive(code_args: Annotated[list[str] | None, typer.Argument(help="Receive code or relay command. Examples: '7121-donor-olympic-bicycle' or '--relay 10.17.62.206:443 7121-donor-olympic-bicycle'. Leave out with --propose.")] = None,
    propose: Annotated[bool, typer.Option("--propose", "-p", help="Make up the code and the encryption password here, show them as a QR code holding the matching send command, then wait for the file and decrypt it.")] = False,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="With --propose: print the code, password and send command as JSON instead of a QR code.")] = False,
    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,
    ) -> None:
    """Receive a file using croc with relay server.
Usage examples:
    devops network receive 7121-donor-olympic-bicycle
    devops network receive -- --relay 10.17.62.206:443 7121-donor-olympic-bicycle
    devops network receive -- croc --relay 10.17.62.206:443 7121-donor-olympic-bicycle
    devops network receive --propose
"""
    if output_json and not propose:
        typer.echo("❌ Error: --json requires --propose.", err=True)
        raise typer.Exit(code=1)
    if propose and code_args:
        typer.echo("❌ Error: --propose makes up its own code; do not pass one.", err=True)
        raise typer.Exit(code=1)
    if install_missing_dependencies:
        from stackops.utils.installer_utils.installer_cli import install_if_missing
        install_if_missing(which="croc", binary_name=None, verbose=True)
    if propose:
        from stackops.scripts.python.helpers.helpers_devops.file_receive_proposal import receive_with_proposed_secrets

        receive_with_proposed_secrets(output_json=output_json)
        return
    import platform
    import shlex
    import sys

    is_windows = platform.system() == "Windows"

    # If no args passed via typer, try to get them from sys.argv directly
    # This handles the case where -- was used and arguments weren't parsed by typer
    if not code_args or (len(code_args) == 1 and code_args[0] in ["--relay", "croc"]):
        # Find the index of 'rx' or 'receive' in sys.argv and get everything after it.
        for i, arg in enumerate(sys.argv):
            if arg in ["rx", "receive", "r"] and i + 1 < len(sys.argv):
                code_args = sys.argv[i + 1:]
                break

    input_str = " ".join(code_args or [])
    try:
        tokens = shlex.split(input_str)
    except ValueError as exc:
        typer.echo(f"❌ Error: Could not parse croc receive code from input: {input_str}", err=True)
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    relay_server: str | None = None
    secret_code: str | None = None
    secret_code_from_env_assignment = False
    croc_command_seen = False

    token_index = 0
    while token_index < len(tokens):
        token = tokens[token_index]
        if token == "--":
            token_index += 1
            continue
        if token == "croc":
            if croc_command_seen:
                typer.echo("❌ Error: Croc receive command may only be provided once.", err=True)
                raise typer.Exit(code=1)
            if secret_code is not None and not secret_code_from_env_assignment:
                typer.echo(f"❌ Error: Unexpected extra argument after croc receive code: {token}", err=True)
                raise typer.Exit(code=1)
            croc_command_seen = True
            token_index += 1
            continue
        if token == "export" and token_index + 1 < len(tokens) and tokens[token_index + 1].startswith("CROC_SECRET="):
            token_index += 1
            continue
        if token == "--relay":
            if relay_server is not None:
                typer.echo("❌ Error: --relay may only be provided once.", err=True)
                raise typer.Exit(code=1)
            if token_index + 1 >= len(tokens) or tokens[token_index + 1].startswith("-"):
                typer.echo("❌ Error: --relay requires a relay server.", err=True)
                raise typer.Exit(code=1)
            relay_server = tokens[token_index + 1]
            token_index += 2
            continue
        if token == "--yes":
            token_index += 1
            continue
        if token.startswith("CROC_SECRET="):
            if secret_code is not None:
                typer.echo("❌ Error: Croc receive code may only be provided once.", err=True)
                raise typer.Exit(code=1)
            secret_code = token.split("=", 1)[1].strip('"').strip("'")
            secret_code_from_env_assignment = True
            token_index += 1
            continue
        if token.startswith("-"):
            typer.echo(f"❌ Error: Unsupported croc receive option: {token}", err=True)
            raise typer.Exit(code=1)
        if secret_code is not None:
            typer.echo(f"❌ Error: Unexpected extra argument after croc receive code: {token}", err=True)
            raise typer.Exit(code=1)
        secret_code = token
        secret_code_from_env_assignment = False
        token_index += 1

    if not secret_code:
        typer.echo(f"❌ Error: Could not parse croc receive code from input: {input_str}", err=True)
        typer.echo("Usage:", err=True)
        typer.echo("  devops network receive 7121-donor-olympic-bicycle", err=True)
        typer.echo("  devops network receive -- --relay 10.17.62.206:443 7121-donor-olympic-bicycle", err=True)
        raise typer.Exit(code=1)

    # Build the appropriate script for current OS
    if is_windows:
        # Windows PowerShell format: croc --relay server:port secret-code --yes
        relay_arg = f"--relay {_quote_powershell_argument(relay_server)}" if relay_server is not None else ""
        code_arg = _quote_powershell_argument(secret_code)
        script = f"""croc {relay_arg} {code_arg} --yes""".strip()
    else:
        # Linux/macOS Bash format: CROC_SECRET="secret-code" croc --relay server:port --yes
        relay_arg = f"--relay {shlex.quote(relay_server)}" if relay_server is not None else ""
        script = f"""export CROC_SECRET={shlex.quote(secret_code)}
croc {relay_arg} --yes""".strip()

    from stackops.utils.code import exit_then_run_shell_script
    from stackops.utils.meta import print_code
    if IS_REPO_DEVELOPER:
        print_code(code=script, desc="🚀 Receiving file with croc", lexer="powershell" if is_windows else "bash")
    exit_then_run_shell_script(script=script, strict=False)


def share_file_send(path: Annotated[str | None, typer.Argument(help="Path to the file or directory to send. Required unless --text is provided.")] = None,
                    zip_folder: Annotated[bool, typer.Option("--zip", "-z", help="Zip folder before sending")] = False,
                    code: Annotated[str | None, typer.Option("--code", "-c", help="Codephrase used to connect to relay")] = None,
                    text: Annotated[str | None, typer.Option("--text", "-t", help="Send some text")] = None,
                    qrcode: Annotated[bool, typer.Option("--qrcode", "--qr", "-q", help="Show receive code as a qrcode")] = False,
                    backend: Annotated[Literal["wormhole", "w", "croc", "c"], typer.Option("--backend", "-b", help="Backend to use")] = "croc",
                    local_relay: Annotated[bool, typer.Option("--local-relay", "-l", help="Relay through this machine's LAN address (port 443) instead of croc's public relay")] = False,
                    encryption: Annotated[EncryptionModeChoice | None, typer.Option("--encryption", "-e", help="GPG-encrypt the file or directory before sending: symmetric/s (password) or asymmetric/a (keys). Unlike --code, it stays encrypted after the transfer.")] = None,
                    pwd: Annotated[str | None, typer.Option("--password", "-p", help="Symmetric GPG password. Prompts with a hidden prompt when omitted.")] = None,
                    recipient: Annotated[str | None, typer.Option("--recipient", "-r", help="Asymmetric GPG recipient key (id, email, or fingerprint). Defaults to your own key.")] = None,
                    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,
                    output_json: Annotated[bool, typer.Option("--json", "-j", help="Emit JSON Lines with transfer code/PID, then completion status.")] = False,
                    timeout: Annotated[float | None, typer.Option("--timeout", "-T", min=1, help="Maximum seconds to wait for transfer completion.")] = None,
                    ) -> None:
    """Send a file, directory, or text."""
    import platform
    import shlex
    import shutil
    from pathlib import Path

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
    if zip_folder and backend in ("wormhole", "w"):
        typer.echo("❌ Error: --zip is only supported with the croc backend.", err=True)
        raise typer.Exit(code=1)

    if local_relay and backend in ("wormhole", "w"):
        typer.echo("❌ Error: --local-relay is only supported with the croc backend.", err=True)
        raise typer.Exit(code=1)
    from stackops.utils.cloud.encryption import parse_encryption_mode

    encryption_mode = None if encryption is None else parse_encryption_mode(encryption, label="encryption")
    if encryption_mode is not None and text is not None:
        typer.echo("❌ Error: --encryption can only be used when sending a file or directory.", err=True)
        raise typer.Exit(code=1)
    if pwd is not None and encryption_mode != "symmetric":
        typer.echo("❌ Error: --password requires --encryption symmetric.", err=True)
        raise typer.Exit(code=1)
    if recipient is not None and encryption_mode != "asymmetric":
        typer.echo("❌ Error: --recipient requires --encryption asymmetric.", err=True)
        raise typer.Exit(code=1)

    relay_endpoint: str | None = None
    if local_relay:
        import stackops.utils.network.address as helper

        local_ip_v4 = helper.select_lan_ipv4(prefer_vpn=False)
        if local_ip_v4 is None:
            typer.echo("❌ Error: Could not determine local LAN IPv4 address for relay.", err=True)
            raise typer.Exit(code=1)
        relay_endpoint = f"{local_ip_v4}:443"

    with_receipts = output_json or timeout is not None
    if with_receipts and install_missing_dependencies and backend in {"croc", "c"}:
        from stackops.scripts.python.helpers.helpers_devops.network_service import install_service_dependency

        install_service_dependency("croc")

    send_target = "text" if text is not None else path
    staging_root: Path | None = None
    if encryption_mode is not None and path is not None:
        from stackops.scripts.python.helpers.helpers_devops.file_send_encryption import stage_encrypted_payload

        encrypted_path = stage_encrypted_payload(path=path, mode=encryption_mode, pwd=pwd, recipient=recipient)
        staging_root = encrypted_path.parent
        path = str(encrypted_path)
        typer.echo(f"🔐 Encrypted with GPG ({encryption_mode}). Receiver decrypts with: devops data decrypt {shlex.quote(encrypted_path.name)} --encryption {encryption_mode}", err=True)

    if with_receipts:
        from stackops.scripts.python.helpers.helpers_devops.file_send_runtime import send_with_receipts

        try:
            send_with_receipts(path=path, text=text, code=code, backend=backend, zip_folder=zip_folder, qrcode=qrcode, relay=relay_endpoint, timeout=timeout, output_json=output_json)
        finally:
            if staging_root is not None:
                shutil.rmtree(staging_root)
        return

    is_windows = platform.system() == "Windows"
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
            receive_hint = f"""uvx --from magic-wormhole wormhole receive {code if code is not None else "<code>"}"""
            print_desc = "🚀 sending file with magic-wormhole"
        case "croc" | "c":
            if install_missing_dependencies:
                from stackops.utils.installer_utils.installer_cli import install_if_missing
                install_if_missing(which="croc", binary_name=None, verbose=True)

            command_parts = ["croc", "send"] if relay_endpoint is None else ["croc", "--relay", relay_endpoint, "send"]
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
            relay_hint = "" if relay_endpoint is None else f" -- --relay {relay_endpoint}"
            receive_hint = f"""devops network receive{relay_hint} {code if code is not None else "<code>"}"""
            print_desc = "🚀 sending file with croc"

    if staging_root is not None:
        cleanup_command = "Remove-Item -Recurse -Force -LiteralPath" if is_windows else "rm -rf"
        script = f"""{script}
{cleanup_command} {quote_shell_arg(str(staging_root))}"""
    typer.echo(f"🚀 Sending {send_target}. Use: {receive_hint}")
    from stackops.utils.code import exit_then_run_shell_script
    from stackops.utils.meta import print_code
    if IS_REPO_DEVELOPER:
        print_code(code=script, desc=print_desc, lexer="powershell" if is_windows else "bash")
    exit_then_run_shell_script(script=script, strict=False)
