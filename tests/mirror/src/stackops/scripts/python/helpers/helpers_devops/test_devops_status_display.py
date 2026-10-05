from io import StringIO

import pytest
from rich.console import Console

from stackops.scripts.python.helpers.helpers_devops import devops_status_display


def test_tools_status_summarizes_catalog_and_lists_each_app_once(monkeypatch: pytest.MonkeyPatch) -> None:
    output = StringIO()
    monkeypatch.setattr(
        devops_status_display,
        "console",
        Console(file=output, width=100, color_system=None),
    )
    grouped_tools = {
        "search": {"installed-only": True, "catalog-only": False},
        "termabc": {"installed-only": True, "catalog-only": False, "tmux": True},
    }

    devops_status_display.display_tools_status(grouped_tools)

    rendered_output = output.getvalue()
    assert "Apps installed" in rendered_output
    assert "2 installed · 3 in catalog" in rendered_output
    assert "Search" in rendered_output
    assert "Termabc" in rendered_output
    assert "Installed apps (2): installed-only, tmux" in rendered_output
    assert "Not installed apps (1): catalog-only" in rendered_output
    assert rendered_output.count("catalog-only") == 1
    assert rendered_output.count("installed-only") == 1
    assert "Missing" not in rendered_output
    assert "Coverage" not in rendered_output
    assert "%" not in rendered_output


def test_tools_status_handles_empty_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    output = StringIO()
    monkeypatch.setattr(
        devops_status_display,
        "console",
        Console(file=output, width=100, color_system=None),
    )

    devops_status_display.display_tools_status({})

    rendered_output = output.getvalue()
    assert "0 installed · 0 in catalog" in rendered_output
    assert "Installed apps (0): None" in rendered_output
    assert "Not installed apps (0): None" in rendered_output
