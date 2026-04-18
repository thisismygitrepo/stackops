import importlib

from typer.testing import CliRunner

parallel_module = importlib.import_module("stackops.scripts.python.agents_parallel")


def test_get_app_registers_expected_commands() -> None:
    app = parallel_module.get_app()
    command_names = {str(command.name) for command in app.registered_commands}

    assert {"create", "c", "create-context", "x", "collect", "T", "make-template", "p"} <= command_names


def test_create_help_mentions_provider_and_agent_options() -> None:
    result = CliRunner().invoke(parallel_module.get_app(), ["create", "--help"])

    assert result.exit_code == 0
    assert "PROVIDER options:" in result.stdout
    assert "AGENT options:" in result.stdout
