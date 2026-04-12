import typer

from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai import update_docs as update_docs_module
from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai import update_installer as update_installer_module
from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai import update_test as update_test_module


def get_app() -> typer.Typer:
    cli_app = typer.Typer(help="🤖 <w> Developer AI workflows.", no_args_is_help=True, add_help_option=True, add_completion=False)
    cli_app.command(
        name="update-installer",
        no_args_is_help=False,
        help="🔄 <u> Create an agents layout for updating installer_data.json.",
    )(update_installer_module.update_installer)
    cli_app.command(name="u", no_args_is_help=False, hidden=True)(update_installer_module.update_installer)
    cli_app.command(
        name="update-test",
        no_args_is_help=False,
        help="🧪 <t> Create an agents layout for writing tests from repo Python sources.",
    )(update_test_module.update_test)
    cli_app.command(name="t", no_args_is_help=False, hidden=True)(update_test_module.update_test)
    cli_app.command(
        name="update-docs",
        no_args_is_help=False,
        help="📚 <d> Create an agents layout for updating CLI and API docs only.",
    )(update_docs_module.update_docs)
    cli_app.command(name="d", no_args_is_help=False, hidden=True)(update_docs_module.update_docs)
    return cli_app
