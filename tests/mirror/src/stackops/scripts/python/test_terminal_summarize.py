import json

from typer.testing import CliRunner

from stackops.scripts.python import terminal


def test_summarize_with_herdr_vocabulary_uses_workspace_vocabulary(tmp_path) -> None:
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

    result = CliRunner().invoke(terminal.get_app(), ["summarize", str(layout_path), "--vocabulary", "herdr"])

    assert result.exit_code == 0
    assert "Herdr Layout Summary" in result.output
    assert "Vocabulary: herdr" in result.output
    assert "Workspaces: 1" in result.output
    assert "Workspace Label" in result.output
    assert "alpha" in result.output


def test_summarize_help_describes_vocabulary_not_backend() -> None:
    result = CliRunner().invoke(terminal.get_app(), ["S", "--help"])

    assert result.exit_code == 0
    assert "--vocabulary" in result.output
    assert "--backend" not in result.output


def test_summarize_accepts_legacy_backend_alias(tmp_path) -> None:
    layout_path = tmp_path / "layouts.json"
    layout_path.write_text(
        json.dumps(
            {
                "version": "0.1",
                "layouts": [
                    {
                        "layoutName": "alpha",
                        "layoutTabs": [{"tabName": "one", "startDir": ".", "command": "echo one"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(terminal.get_app(), ["summarize", str(layout_path), "--backend", "herdr"])

    assert result.exit_code == 0
    assert "Vocabulary: herdr" in result.output
    assert "Workspaces: 1" in result.output
