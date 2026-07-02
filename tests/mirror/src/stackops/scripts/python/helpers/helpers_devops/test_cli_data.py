import re

from typer.testing import CliRunner

from stackops.scripts.python import devops
from stackops.scripts.python.helpers.helpers_devops import cli_data


def test_data_register_exposes_only_encryption_mode() -> None:
    app = devops.get_app()
    help_result = CliRunner().invoke(app, ["data", "register", "--help"])
    removed_option_result = CliRunner().invoke(app, ["data", "register", "--no-encrypt"])

    assert help_result.exit_code == 0
    assert re.search(r"--encryption\s+-e", help_result.output) is not None
    assert "--no-encrypt" not in help_result.output
    assert removed_option_result.exit_code == 2
    assert "No such option: --no-encrypt" in removed_option_result.output


def test_data_subset_help_exposes_source_and_conflict_options() -> None:
    runner = CliRunner()

    result = runner.invoke(cli_data.get_app(), ["subset", "--help"])
    alias_result = runner.invoke(cli_data.get_app(), ["u", "--help"])

    assert result.exit_code == 0
    assert alias_result.exit_code == 0
    assert "OUTPUT_PATH" in result.output
    assert "--source" in result.output
    assert "-s" in result.output
    assert "--on-conflict" in result.output
    assert "-o" in result.output
    assert "--which" in result.output
    assert "-w" in result.output
    assert "--append" not in result.output
    assert "--overwrite" not in result.output
    assert "Create a backup configuration from selected data entries." in alias_result.output
