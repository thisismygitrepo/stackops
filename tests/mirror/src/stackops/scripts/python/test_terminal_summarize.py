import json

from typer.testing import CliRunner

from stackops.scripts.python import terminal


def test_summarize_with_herdr_backend_uses_workspace_vocabulary(tmp_path) -> None:
    layout_path = tmp_path / "layouts.json"
    layout_path.write_text(
        json.dumps(
            {
                "version": "0.1",
                "layouts": [
                    {
                        "layoutName": "alpha",
                        "layoutTabs": [
                            {"tabName": "one", "startDir": ".", "command": "echo one"},
                            {"tabName": "two", "startDir": ".", "command": "echo two"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(terminal.get_app(), ["summarize", str(layout_path), "--backend", "herdr"])

    assert result.exit_code == 0
    assert "Herdr Layout Summary" in result.output
    assert "Backend: herdr" in result.output
    assert "Workspaces: 1" in result.output
    assert "Workspace Label" in result.output
    assert "alpha" in result.output
