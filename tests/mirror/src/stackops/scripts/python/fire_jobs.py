from typer.testing import CliRunner

import stackops.scripts.python.fire_jobs as fire_jobs_app


def test_fire_help_omits_removed_options() -> None:
    result = CliRunner().invoke(fire_jobs_app.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "--zellij-tab" not in result.stdout
    assert "--submit-to-cloud" not in result.stdout


def test_fire_rejects_removed_options() -> None:
    result = CliRunner().invoke(
        fire_jobs_app.get_app(),
        ["--zellij-tab", "jobs", "--submit-to-cloud", "demo.py"],
    )

    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
