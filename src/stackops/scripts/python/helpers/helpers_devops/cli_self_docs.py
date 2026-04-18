from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal

import typer
import stackops.scripts.python.graph as graph_assets
from stackops.scripts.python.graph import CLI_GRAPH_PATH_REFERENCE
from stackops.utils.path_reference import get_path_reference_library_relative_path


DOCS_BIND_ADDRESS = "0.0.0.0"
DOCS_PORT = 8000
DOCS_SITE_PATH = "/stackops/"
DOCS_CONFIG_FILE_NAME = "zensical.toml"
CLI_GRAPH_RELATIVE_PATH = Path("src", "stackops").joinpath(
    get_path_reference_library_relative_path(module=graph_assets, path_reference=CLI_GRAPH_PATH_REFERENCE)
)
DOCS_ARTIFACT_TEMPLATE = "plotly_dark"


@dataclass(frozen=True, slots=True)
class DocsArtifactSpec:
    view: Literal["sunburst", "treemap", "icicle"]
    output_relative_path: Path


DOCS_ARTIFACT_SPECS: tuple[DocsArtifactSpec, ...] = (
    DocsArtifactSpec(view="sunburst", output_relative_path=Path("docs/assets/devops-self-explore/sunburst.html")),
    # DocsArtifactSpec(view="treemap", output_relative_path=Path("docs/assets/devops-self-explore/treemap.html")),
    # DocsArtifactSpec(view="icicle", output_relative_path=Path("docs/assets/devops-self-explore/icicle.html")),
)


def _build_docs_url(host: str) -> str:
    return f"http://{host}:{DOCS_PORT}{DOCS_SITE_PATH}"


def get_docs_repo_root() -> Path:
    from stackops.utils.source_of_truth import REPO_ROOT

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
    from stackops.scripts.python.helpers.helpers_network import address as address_helper

    localhost_url = _build_docs_url("127.0.0.1")
    typer.echo(f"""Local docs URL: {localhost_url}""")

    lan_ipv4 = address_helper.select_lan_ipv4(prefer_vpn=False)
    if lan_ipv4 is None:
        return
    _display_docs_url(_build_docs_url(lan_ipv4))


def write_cli_graph_snapshot(repo_root: Path) -> Path:
    from stackops.scripts.python.graph.generate_cli_graph import build_cli_graph

    cli_graph_path = repo_root.joinpath(CLI_GRAPH_RELATIVE_PATH)
    cli_graph_payload = build_cli_graph()
    cli_graph_path.write_text(
        json.dumps(cli_graph_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"""Regenerated CLI graph snapshot: {cli_graph_path.relative_to(repo_root).as_posix()}""")
    return cli_graph_path


def render_docs_artifact(repo_root: Path, artifact_spec: DocsArtifactSpec) -> Path:
    from stackops.scripts.python.graph.visualize.plotly_views import use_render_plotly

    output_path = repo_root.joinpath(artifact_spec.output_relative_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    use_render_plotly(
        view=artifact_spec.view,
        output=str(output_path),
        template=DOCS_ARTIFACT_TEMPLATE,
        path=None,
        max_depth=None,
        uv_with=None,
        uv_project_dir=None,
    )
    typer.echo(f"""Regenerated docs artifact: {output_path.relative_to(repo_root).as_posix()}""")
    return output_path


def create_docs_artifacts(repo_root: Path) -> list[Path]:
    write_cli_graph_snapshot(repo_root=repo_root)
    generated_paths = [render_docs_artifact(repo_root=repo_root, artifact_spec=artifact_spec) for artifact_spec in DOCS_ARTIFACT_SPECS]
    return generated_paths


def serve_docs(rebuild: bool, create_artifacts: bool) -> None:
    import platform

    from stackops.utils.code import exit_then_run_shell_script, get_uv_command

    repo_root = get_docs_repo_root()
    _print_docs_urls()
    uv_command = get_uv_command(platform=platform.system()).strip()
    if create_artifacts:
        create_docs_artifacts(repo_root=repo_root)
    rebuild_command = ""
    if rebuild:
        rebuild_command = f"""{uv_command} run zensical build
"""
    command = f"""
cd "{repo_root}"
{rebuild_command}{uv_command} run zensical serve -a {DOCS_BIND_ADDRESS}:{DOCS_PORT}
"""
    exit_then_run_shell_script(script=command, strict=False)
