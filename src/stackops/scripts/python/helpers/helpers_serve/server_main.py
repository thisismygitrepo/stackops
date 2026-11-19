def run_server(host: str, port: int, open_browser: bool, stackops_executable: str, working_directory: str) -> None:
    import secrets
    import socket
    import webbrowser

    import uvicorn
    from rich.console import Console
    from rich.panel import Panel

    from stackops.scripts.python.helpers.helpers_serve.constants import GRACEFUL_SHUTDOWN_SECONDS, PORT_PROBE_SECONDS, TOKEN_COOKIE_PREFIX
    from stackops.scripts.python.helpers.helpers_serve.server_app import create_app
    from stackops.utils.network.address import select_lan_ipv4

    console = Console()
    is_ipv6 = ":" in host
    family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
    local_host = "127.0.0.1" if host == "0.0.0.0" else "::1" if host == "::" else host
    try:
        # macOS lets an all-interfaces listener and a loopback one share a port without an error, and the loopback one then takes every local connection.
        with socket.socket(family) as probe:
            probe.settimeout(PORT_PROBE_SECONDS)
            if port != 0 and probe.connect_ex((local_host, port)) == 0:
                raise OSError(f"""another server already answers on {local_host}:{port}""")
        listener = socket.create_server((host, port), family=family)
    except OSError as error:
        console.print(f"""[red]Cannot listen on {host}:{port}[/red] ({error}). Choose another port with --port, or --port 0 for a free one.""")
        raise SystemExit(1) from error
    bound_port: int = listener.getsockname()[1]
    token = secrets.token_urlsafe(32)
    url_host = "localhost" if host in ("0.0.0.0", "::") else f"""[{host}]""" if is_ipv6 else host
    url = f"""http://{url_host}:{bound_port}/?token={token}"""
    exposure_note = (
        ""
        if host in ("127.0.0.1", "::1", "localhost")
        else f"""\n[yellow]Listening on {host}: anyone who can reach this port and has the link can run commands on this machine, over plain HTTP.[/yellow]"""
    )
    console.print(Panel("[bold]StackOps web UI[/bold]  [dim]Ctrl+C stops the server and the commands it is running.[/dim]", border_style="blue", expand=False))
    lan_address = select_lan_ipv4(prefer_vpn=False) if host == "0.0.0.0" else None
    if lan_address is None:
        console.print(url, soft_wrap=True, highlight=False, markup=False)
    else:
        console.print("[bold]On this machine[/bold]")
        console.print(url, soft_wrap=True, highlight=False, markup=False)
        console.print("[bold]From other devices on the network[/bold]")
        console.print(f"""http://{lan_address}:{bound_port}/?token={token}""", soft_wrap=True, highlight=False, markup=False)
    console.print(f"""[dim]The link carries this session's access token and changes on every start.[/dim]{exposure_note}""")
    app = create_app(
        token=token, cookie_name=f"""{TOKEN_COOKIE_PREFIX}_{bound_port}""", stackops_executable=stackops_executable, working_directory=working_directory
    )
    if open_browser:
        webbrowser.open(url)
    config = uvicorn.Config(app, log_level="warning", access_log=False, ws="websockets-sansio", timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS)
    uvicorn.Server(config).run(sockets=[listener])
