import pytest
import typer

from stackops.utils.cli_utils import command_lookup
from stackops.utils.installer_utils import installer_cli


def test_check_installations_group_agents_table(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    installed_tools = {"headroom", "tmux"}

    def fake_check_tool_exists(tool_name: str) -> bool:
        return tool_name in installed_tools

    monkeypatch.setattr(command_lookup, "check_tool_exists", fake_check_tool_exists)

    installer_cli.check_installations(which="agents", group=True)

    output = capsys.readouterr().out
    assert "CLI Check" in output
    assert "beads" in output
    assert "gastown" in output
    assert "headroom" in output
    assert "herdr" in output
    assert "tmux" in output
    assert "✅" in output
    assert "❌" in output


def test_check_installations_unknown_group_raises() -> None:
    with pytest.raises(typer.BadParameter):
        installer_cli.check_installations(which="missing", group=True)
