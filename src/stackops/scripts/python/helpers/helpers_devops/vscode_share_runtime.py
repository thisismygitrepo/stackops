import json
import subprocess
import time
from typing import cast
from urllib.parse import quote

import typer

from stackops.scripts.python.helpers.helpers_devops.network_service import start_service, stop_services


def read_tunnel_status(cli_data_dir: str | None, timeout: float) -> dict[str, object]:
    arguments = ["code", "tunnel", "status"]
    if cli_data_dir is not None:
        arguments.extend(["--cli-data-dir", cli_data_dir])
    result = subprocess.run(arguments, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"VS Code status failed with code {result.returncode}: {result.stderr.strip()}")
    payload: object = json.loads(result.stdout)
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise RuntimeError("VS Code status returned an invalid JSON object.")
    return cast(dict[str, object], payload)


def run_vscode_tunnel(
    *, arguments: list[str], action: str, cli_data_dir: str | None,
    name: str | None, background: bool, output_json: bool, timeout: float,
) -> None:
    try:
        if action == "status":
            typer.echo(json.dumps(read_tunnel_status(cli_data_dir, timeout), indent=2))
            return
        if action in {"install-service", "uninstall-service"}:
            result = subprocess.run(arguments, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=timeout)
            if result.returncode != 0:
                raise RuntimeError(f"VS Code {action} failed with code {result.returncode}: {result.stderr.strip()}")
            receipt: dict[str, object] = {"status": "completed", "action": action, "state": read_tunnel_status(cli_data_dir, timeout)}
            typer.echo(json.dumps(receipt) if output_json else f"VS Code {action} completed.")
            return
        current = read_tunnel_status(cli_data_dir, timeout)
        if current.get("tunnel") is not None:
            raise typer.BadParameter("A VS Code tunnel is already running; inspect it with vscode-share status.")
        service = start_service("vscode-tunnel", arguments, background, None)
        leave_running = False
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if service.process.poll() is not None:
                    raise RuntimeError(f"VS Code exited with code {service.process.returncode}; see {service.log_path}.")
                state = read_tunnel_status(cli_data_dir, max(0.1, deadline - time.monotonic()))
                tunnel = state.get("tunnel")
                if isinstance(tunnel, dict) and tunnel.get("tunnel") == "Connected":
                    tunnel_name = tunnel.get("name")
                    if name is not None and tunnel_name != name:
                        raise RuntimeError("The running tunnel name differs from --name.")
                    url = f"https://vscode.dev/tunnel/{quote(tunnel_name, safe='')}" if isinstance(tunnel_name, str) else None
                    receipt = {"status": "ready", "url": url, "pid": service.process.pid, "log_path": str(service.log_path), "background": background, "state": state}
                    typer.echo(json.dumps(receipt) if output_json else f"Ready: {url} (PID {service.process.pid}, log {service.log_path})")
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f"VS Code tunnel did not become ready within {timeout:g}s; see {service.log_path}.")
            if background:
                leave_running = True
                return
            returncode = service.process.wait()
            if returncode != 0:
                raise typer.Exit(returncode if returncode > 0 else 128 - returncode)
        finally:
            if not leave_running:
                stop_services([service])
    except KeyboardInterrupt:
        raise typer.Exit(130) from None
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as failure:
        typer.echo(f"VS Code operation failed: {failure}", err=True)
        raise typer.Exit(1) from None
