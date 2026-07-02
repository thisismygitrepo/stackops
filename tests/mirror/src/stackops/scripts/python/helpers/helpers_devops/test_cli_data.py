import re

from typer.testing import CliRunner

from stackops.scripts.python import devops


def test_data_register_exposes_only_encryption_mode() -> None:
    app = devops.get_app()
    help_result = CliRunner().invoke(app, ["data", "register", "--help"])
    removed_option_result = CliRunner().invoke(app, ["data", "register", "--no-encrypt"])

    assert help_result.exit_code == 0
    assert re.search(r"--encryption\s+-e", help_result.output) is not None
    assert "--no-encrypt" not in help_result.output
    assert removed_option_result.exit_code == 2
    assert "No such option: --no-encrypt" in removed_option_result.output
