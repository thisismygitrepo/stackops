from pathlib import Path

import typer


DOCS_BIND_ADDRESS = "0.0.0.0"
DOCS_PORT = 8000
DOCS_SITE_PATH = "/machineconfig/"
DOCS_CONFIG_FILE_NAME = "zensical.toml"


def _build_docs_url(host: str) -> str:
    return f"http://{host}:{DOCS_PORT}{DOCS_SITE_PATH}"


def get_docs_repo_root() -> Path:
    from machineconfig.utils.source_of_truth import REPO_ROOT

    docs_dir = REPO_ROOT.joinpath("docs")
    docs_config_path = REPO_ROOT.joinpath(DOCS_CONFIG_FILE_NAME)
    if not docs_dir.exists() or not docs_config_path.exists():
        typer.echo(f"""❌ ERROR: Could not find docs sources under "{REPO_ROOT}".""", err=True)
        raise typer.Exit(code=1)
    return REPO_ROOT


def _display_docs_url(url: str) -> None:
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()
    url_text = Text(url, style="bold bright_cyan underline")
    message = Text.assemble(("🚀 ", "bright_red"), url_text, (" 🚀", "bright_red"))
    panel = Panel(
        Align.center(message),
        title="[bold bright_green]🌐 Local Network Docs URL 🌐[/bold bright_green]",
        subtitle="[italic bright_yellow]⚡ Open the link above to preview the docs! ⚡[/italic bright_yellow]",
        border_style="bright_magenta",
        padding=(1, 2),
        expand=False,
    )
    console.print(panel)


def _print_docs_urls() -> None:
    from machineconfig.scripts.python.helpers.helpers_network import address as address_helper

    localhost_url = _build_docs_url("127.0.0.1")
    typer.echo(f"""Local docs URL: {localhost_url}""")

    lan_ipv4 = address_helper.select_lan_ipv4(prefer_vpn=False)
    if lan_ipv4 is None:
        return
    _display_docs_url(_build_docs_url(lan_ipv4))


def serve_docs(rebuild: bool) -> None:
    import platform

    from machineconfig.utils.code import exit_then_run_shell_script, get_uv_command
    from machineconfig.scripts.python.helpers.helpers_devops.docs_changelog import sync_docs_changelog

    repo_root = get_docs_repo_root()
    _print_docs_urls()
    uv_command = get_uv_command(platform=platform.system()).strip()
    rebuild_command = ""
    if rebuild:
        sync_docs_changelog(repo_root=repo_root)
        rebuild_command = f"""{uv_command} run zensical build
"""
    command = f"""
cd "{repo_root}"
{rebuild_command}{uv_command} run zensical serve -a {DOCS_BIND_ADDRESS}:{DOCS_PORT}
"""
    exit_then_run_shell_script(script=command, strict=False)
