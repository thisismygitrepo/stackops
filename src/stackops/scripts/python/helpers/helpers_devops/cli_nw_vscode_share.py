import platform
import secrets
import shlex
from pathlib import Path
from typing import Final
from urllib.parse import quote

import typer

SERVE_WEB_USUAL_PORT: Final[int] = 8000


def resolve_serve_web_auth(extra_args: str, token: str | None, token_file: str | None, no_auth: bool) -> tuple[str, str | None]:
    if any(
        item == option or item.startswith(f"{option}=")
        for item in shlex.split(extra_args)
        for option in ("--connection-token", "--connection-token-file", "--without-connection-token")
    ):
        raise typer.BadParameter("Pass --token, --token-file or --no-auth to vscode-share instead of connection token options through --extra-args", param_hint="--extra-args")
    if sum((token is not None, token_file is not None, no_auth)) > 1:
        raise typer.BadParameter("--token, --token-file and --no-auth are mutually exclusive.")
    if no_auth:
        return "--without-connection-token", None
    if token_file is not None:
        token_path = Path(token_file).expanduser().resolve(strict=False)
        if not token_path.is_file():
            raise typer.BadParameter(f"File not found: {token_path}", param_hint="--token-file")
        return f"--connection-token-file {shlex.quote(str(token_path))}", token_path.read_text(encoding="utf-8").strip()
    connection_token = secrets.token_urlsafe(16) if token is None else token
    return f"--connection-token {shlex.quote(connection_token)}", connection_token


def resolve_serve_web_port_part(extra_args: str, host: str) -> str:
    if _extract_option_value(shlex.split(extra_args), "--port") is not None:
        return ""
    from stackops.scripts.python.helpers.helpers_devops.network_service import find_free_port

    return f"--port {find_free_port(host=host, preferred_port=SERVE_WEB_USUAL_PORT)}"


def _extract_option_value(args: list[str], option: str) -> str | None:
    for index, token in enumerate(args):
        if token == option and index + 1 < len(args):
            return args[index + 1]
        if token.startswith(f"{option}="):
            return token.split("=", 1)[1]
    return None


def get_serve_web_details(cmd: str) -> tuple[str, int, str]:
    tokens = shlex.split(cmd)
    host = _extract_option_value(tokens, "--host") or "localhost"
    port_raw = _extract_option_value(tokens, "--port")
    server_base_path = _extract_option_value(tokens, "--server-base-path") or ""

    try:
        port = int(port_raw) if port_raw is not None else SERVE_WEB_USUAL_PORT
    except ValueError:
        port = SERVE_WEB_USUAL_PORT

    return host, port, server_base_path


def _normalize_server_base_path(server_base_path: str) -> str:
    trimmed = server_base_path.strip()
    if trimmed in {"", "/"}:
        return ""
    return "/" + trimmed.strip("/")


def resolve_share_local_folder(directory: str | None) -> str:
    if directory is None or directory.strip() == "":
        return str(Path.cwd().resolve())
    return str(Path(directory).expanduser().resolve(strict=False))


def build_http_url(host: str, port: int, server_base_path: str, folder_path: str | None, connection_token: str | None) -> str:
    normalized_path = _normalize_server_base_path(server_base_path)
    suffix = "/" if normalized_path == "" else f"{normalized_path}/"
    query_parts: list[str] = []
    if connection_token is not None:
        query_parts.append(f"tkn={quote(connection_token, safe='')}")
    if folder_path is not None:
        query_parts.append(f"folder={quote(folder_path, safe='/:')}")
    url = f"http://{host}:{port}{suffix}"
    return url if len(query_parts) == 0 else f"{url}?{'&'.join(query_parts)}"


def print_serve_web_urls(cmd: str, folder_path: str | None, connection_token: str | None) -> None:
    from rich import box
    from rich.console import Console, ConsoleRenderable, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    import stackops.utils.network.address as helper

    host, port, server_base_path = get_serve_web_details(cmd)
    normalized_host = host.strip().lower()
    base_path_note = _normalize_server_base_path(server_base_path) or "/"
    console = Console()
    address_warning: Text | None = None

    if port == 0:
        console.print(
            Panel(
                Group(
                    Text("`code serve-web` is configured to pick a random free port.", style="bold yellow"),
                    Text("The final clickable URL will only be known after the server starts.", style="yellow"),
                    Text(f"Base path: {base_path_note}", style="dim"),
                    Text(f"Folder: {folder_path}", style="dim") if folder_path is not None else Text("", style="dim"),
                ),
                title="VS Code Web URLs",
                border_style="yellow",
            )
        )
        return

    urls: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    def add_url(label: str, target_host: str) -> None:
        url = build_http_url(target_host, port, server_base_path, folder_path, connection_token)
        if url in seen_urls:
            return
        seen_urls.add(url)
        urls.append((label, url))

    try:
        all_ipv4 = helper.get_all_ipv4_addresses()
    except Exception as exc:
        all_ipv4 = []
        address_warning = Text(f"Could not enumerate interface IPv4 addresses: {exc}", style="yellow")

    if normalized_host in {"", "localhost", "127.0.0.1"}:
        add_url("Localhost", "localhost")
        for iface, ip in all_ipv4:
            if ip.startswith("127."):
                add_url(iface, ip)
    elif normalized_host == "0.0.0.0":
        add_url("Localhost", "localhost")
        computer_name = platform.node().strip()
        if computer_name:
            add_url("Hostname", computer_name)
        for iface, ip in all_ipv4:
            if ip.startswith("127."):
                continue
            add_url(iface, ip)
    else:
        add_url("Configured host", host)

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Target", style="cyan", no_wrap=True)
    table.add_column("URL", style="bright_blue")

    for label, url in urls:
        link_text = Text(url, style="bold bright_blue")
        link_text.stylize(f"link {url}")
        table.add_row(label, link_text)

    binding_note = (
        f"Bound to {host}. Open these after the server starts."
        if normalized_host != "0.0.0.0"
        else "Bound to 0.0.0.0, so localhost and each non-loopback IPv4 can be used from this machine or your LAN."
    )
    auth_note = "none" if connection_token is None else "connection token, included in the URLs"
    note = Text(f"Base path: {base_path_note}    Port: {port}    Auth: {auth_note}", style="dim")
    body: list[ConsoleRenderable] = [Text(binding_note, style="bold green"), table]
    if address_warning is not None:
        body.append(address_warning)
    if folder_path is not None:
        body.append(Text(f"Folder: {folder_path}", style="dim"))
    body.append(note)

    console.print(
        Panel(
            Group(*body),
            title="VS Code Web URLs",
            border_style="green",
        )
    )
