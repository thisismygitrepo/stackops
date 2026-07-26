import shlex
import subprocess
from typing import Literal


type VscodeTunnelProvider = Literal["GitHub Account", "Microsoft Account"]


def get_vscode_tunnel_provider(cli_data_dir: str | None) -> VscodeTunnelProvider | None:
    command = ["code", "tunnel", "user", "show"]
    if cli_data_dir is not None:
        command.extend(("--cli-data-dir", cli_data_dir))

    result: subprocess.CompletedProcess[str] = subprocess.run(command, capture_output=True, text=True, check=False)
    output = result.stdout.strip()
    match output:
        case "not logged in":
            return None
        case "logged in with provider GitHub Account":
            return "GitHub Account"
        case "logged in with provider Microsoft Account":
            return "Microsoft Account"
        case _:
            detail = result.stderr.strip() or output or f"process exited with status {result.returncode}"
            raise RuntimeError(f"Could not determine the VS Code tunnel credential provider: {detail}")


def print_vscode_tunnel_credential_context(cli_data_dir: str | None) -> None:
    from rich.console import Console
    from rich.panel import Panel

    provider = get_vscode_tunnel_provider(cli_data_dir)
    if provider is None:
        body = "No stored tunnel credential. VS Code will ask you to sign in and choose an account before creating the tunnel."
        border_style = "yellow"
    else:
        match provider:
            case "GitHub Account":
                provider_option = "github"
            case "Microsoft Account":
                provider_option = "microsoft"
        cli_data_dir_option = f" --cli-data-dir {shlex.quote(cli_data_dir)}" if cli_data_dir is not None else ""
        body = f"""Stored provider: {provider}
Exact username/email: not exposed by the VS Code CLI.

To guarantee the intended account, run:
  code tunnel user logout{cli_data_dir_option}
  code tunnel user login --provider {provider_option}{cli_data_dir_option}"""
        border_style = "green"
    Console().print(Panel(body, title="VS Code Tunnel Credential", border_style=border_style))
