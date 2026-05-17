from typer.testing import CliRunner

from stackops.scripts.python.graph.visualize import cli_graph_app


def test_view_rejects_negative_max_depth() -> None:
    result = CliRunner().invoke(cli_graph_app.get_app(), ["view", "sunburst", "--max-depth", "-1"])

    assert result.exit_code == 2
    assert "Invalid value for '--max-depth' / '-d'" in result.output
    assert "x>=0" in result.output
