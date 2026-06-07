import json
from inspect import Parameter, signature
from pathlib import Path
from typing import get_args

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_config, cli_config_secrets


def test_config_secrets_is_nested_typer_app() -> None:
    runner = CliRunner()

    result = runner.invoke(cli_config.get_app(), ["secrets", "--help"])

    assert result.exit_code == 0
    assert "Usage: root secrets [OPTIONS] COMMAND [ARGS]..." in result.output
    assert "search" in result.output
    assert "stats" in result.output
    assert "add" in result.output
    assert "edit" in result.output
    assert "Examples:" not in result.output


def test_config_secrets_search_help_has_examples() -> None:
    runner = CliRunner()

    result = runner.invoke(cli_config.get_app(), ["secrets", "search", "--help"])

    assert result.exit_code == 0
    assert "Usage: root secrets search [OPTIONS] [TERMS]..." in result.output
    assert "Examples:" in result.output
    assert "devops config secrets search aws dev iam-access-key" in result.output
    assert "devops config secrets add" not in result.output
    assert "devops config secrets edit" not in result.output


def test_secrets_search_keeps_selector_aliases() -> None:
    parameters = signature(cli_config_secrets.search).parameters
    expected_aliases = {
        "secrets_path": "-p",
        "secrets_source": "-s",
        "interactive": "-i",
        "preview_secrets": "-P",
        "verbose": "-v",
        "login_name": "-n",
        "secret_name": "-N",
        "tags": "-t",
        "login_tags": "-l",
        "secret_tags": "-T",
        "scopes": "-S",
        "keys": "-k",
    }

    for parameter_name, alias in expected_aliases.items():
        assert alias in _option_param_decls(parameters[parameter_name])
    assert "add" not in parameters
    assert "edit" not in parameters
    assert "create" not in parameters
    assert "editor" not in parameters


def test_secrets_add_and_edit_have_short_aliases() -> None:
    stats_parameters = signature(cli_config_secrets.stats).parameters
    add_parameters = signature(cli_config_secrets.add).parameters
    edit_parameters = signature(cli_config_secrets.edit).parameters

    assert "-p" in _option_param_decls(stats_parameters["secrets_path"])
    assert "-s" in _option_param_decls(stats_parameters["secrets_source"])
    assert "-d" in _option_param_decls(stats_parameters["details"])
    assert "-p" in _option_param_decls(add_parameters["secrets_path"])
    assert "-s" in _option_param_decls(add_parameters["secrets_source"])
    assert "-p" in _option_param_decls(edit_parameters["secrets_path"])
    assert "-s" in _option_param_decls(edit_parameters["secrets_source"])
    assert "-E" in _option_param_decls(edit_parameters["editor"])


def test_secrets_search_writes_selected_env_handoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps(
            {
                "version": "0.5",
                "entries": [
                    {
                        "name": "aws-dev",
                        "tags": ["aws", "dev"],
                        "secrets": [
                            {
                                "name": "iam-access-key",
                                "tags": ["iam-access-key"],
                                "scopes": ["aws"],
                                "keyValues": {"AWS_ACCESS_KEY_ID": "dummy-key"},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    handoff: list[dict[str, object]] = []
    monkeypatch.setattr(cli_config_secrets.secret_actions, "write_env_handoff", handoff.append)

    cli_config_secrets.search(terms=["aws", "dev"], secrets_path=secrets_path, secrets_source="local")

    assert handoff == [{"AWS_ACCESS_KEY_ID": "dummy-key"}]


def test_secrets_stats_uses_aggregate_tables_without_secret_values(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps(
            {
                "version": "0.5",
                "entries": [
                    {
                        "name": "service-login",
                        "tags": ["team-a"],
                        "description": "Used by service tests",
                        "secrets": [
                            {
                                "name": "service-token",
                                "tags": ["api"],
                                "scopes": ["ci"],
                                "keyValues": {
                                    "SERVICE_TOKEN": "super-secret-token",
                                    "SERVICE_PAYLOAD": {"nested": "do-not-print"},
                                },
                                "rotation": {"lastRotated": "2026-01-01", "rotateEveryDays": 90},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(cli_config_secrets.get_app(), ["stats", "--path", str(secrets_path), "--source", "local"])

    assert result.exit_code == 0
    assert "StackOps Secrets Sources" in result.output
    assert "Inventory Totals" in result.output
    assert "Metadata Coverage" in result.output
    assert "Env Vars" in result.output
    assert "2" in result.output
    assert str(secrets_path) not in result.output
    assert "super-secret-token" not in result.output
    assert "do-not-print" not in result.output
    assert "SERVICE_TOKEN" not in result.output
    assert "service-login" not in result.output
    assert "service-token" not in result.output


def _option_param_decls(parameter: Parameter) -> tuple[str, ...]:
    for metadata in get_args(parameter.annotation)[1:]:
        param_decls = getattr(metadata, "param_decls", ())
        if param_decls:
            return tuple(param_decls)
    raise AssertionError(f"Parameter has no Typer option metadata: {parameter.name}")
