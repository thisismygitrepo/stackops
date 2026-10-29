from typer.testing import CliRunner

from stackops.scripts.python.seek import get_app


def test_semantic_backend_option_is_registered_with_short_flag_and_all_backends() -> None:
    result = CliRunner().invoke(get_app(), ["--help"], terminal_width=200)

    assert result.exit_code == 0
    assert "--semantic-backend" in result.output
    assert "-b" in result.output
    for backend in ("semtools", "ck", "grepai", "qmd"):
        assert backend in result.output


def test_unknown_semantic_backend_is_rejected_before_any_search_runs() -> None:
    result = CliRunner().invoke(get_app(), [".", "query", "--semantic", "--semantic-backend", "nope"])

    assert result.exit_code == 2
    assert "nope" in result.output
