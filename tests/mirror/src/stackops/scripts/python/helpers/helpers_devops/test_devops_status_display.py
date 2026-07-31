from io import StringIO

import pytest
from rich.console import Console

from stackops.scripts.python.helpers.helpers_devops import devops_status_display


def test_tools_status_summarizes_groups_and_lists_each_missing_tool_once(monkeypatch: pytest.MonkeyPatch) -> None:
    output = StringIO()
    monkeypatch.setattr(
        devops_status_display,
        "console",
        Console(file=output, width=100, color_system=None),
    )
    grouped_tools = {
        "search": {"installed-only": True, "missing-tool": False},
        "termabc": {"installed-only": True, "missing-tool": False, "tmux": True},
    }

    devops_status_display.display_tools_status(grouped_tools)

    rendered_output = output.getvalue()
    assert "2/3 unique installed (67%)" in rendered_output
    assert "Search" in rendered_output
    assert "Termabc" in rendered_output
    assert rendered_output.count("missing-tool") == 1
    assert "installed-only" not in rendered_output
