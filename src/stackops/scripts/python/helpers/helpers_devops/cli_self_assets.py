from pathlib import Path

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_self_docs


SUNBURST_OUTPUT_RELATIVE_PATH = Path("docs/assets/devops-self-explore/sunburst.html")


def update_cli_graph() -> None:
    """🧩 <g> Regenerate the checked-in CLI graph snapshot."""
    repo_root = cli_self_docs.get_docs_repo_root()
    cli_self_docs.write_cli_graph_snapshot(repo_root=repo_root)


def regenerate_charts() -> None:
    """☀ <c> Regenerate the checked-in sunburst HTML chart."""
    repo_root = cli_self_docs.get_docs_repo_root()
    cli_self_docs.render_docs_artifact(
        repo_root=repo_root,
        artifact_spec=cli_self_docs.DocsArtifactSpec(
            view="sunburst",
            output_relative_path=SUNBURST_OUTPUT_RELATIVE_PATH,
        ),
    )


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🗂 <a> Regenerate repo-local CLI graph assets.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    cli_app.command(
        name="update-cli-graph",
        no_args_is_help=False,
        help="🧩 <g> Regenerate the checked-in CLI graph snapshot.",
    )(update_cli_graph)
    cli_app.command(
        name="g",
        no_args_is_help=False,
        help="Regenerate the checked-in CLI graph snapshot.",
        hidden=True,
    )(update_cli_graph)
    cli_app.command(
        name="regenerate-charts",
        no_args_is_help=False,
        help="☀ <c> Regenerate the checked-in sunburst HTML chart.",
    )(regenerate_charts)
    cli_app.command(
        name="c",
        no_args_is_help=False,
        help="Regenerate the checked-in sunburst HTML chart.",
        hidden=True,
    )(regenerate_charts)
    return cli_app
