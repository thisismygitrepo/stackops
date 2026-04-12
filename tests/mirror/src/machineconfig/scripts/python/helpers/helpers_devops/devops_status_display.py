from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from rich.panel import Panel

from machineconfig.scripts.python.helpers.helpers_devops import devops_status_display as module


@dataclass
class FakeConsole:
    printed: list[tuple[object, ...]] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)

    def print(self, *objects: object) -> None:
        self.printed.append(objects)

    def rule(self, title: str) -> None:
        self.rules.append(title)


def test_display_report_header_and_footer_print_panels(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(module, "console", fake_console)

    module.display_report_header()
    module.display_report_footer()

    assert isinstance(fake_console.printed[1][0], Panel)
    assert isinstance(fake_console.printed[4][0], Panel)
    assert "Machine Status Report" in str(fake_console.printed[1][0].renderable)
    assert "Status report complete" in str(fake_console.printed[4][0].renderable)


def test_display_repos_status_warns_when_repos_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(module, "console", fake_console)

    module.display_repos_status({"configured": False, "count": 0, "repos": []})

    panel = fake_console.printed[0][0]
    assert isinstance(panel, Panel)
    assert fake_console.rules == ["[bold cyan]📚 Configured Repositories[/bold cyan]"]
    assert str(panel.title) == "Repositories"
    assert str(panel.border_style) == "yellow"


def test_display_config_files_status_uses_green_border_for_high_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(module, "console", fake_console)

    module.display_config_files_status(
        {
            "public_count": 4,
            "public_linked": 4,
            "private_count": 1,
            "private_linked": 1,
        }
    )

    panel = fake_console.printed[0][0]
    assert isinstance(panel, Panel)
    assert str(panel.border_style) == "green"
    assert "100% configured" in str(panel.title)


def test_display_tools_status_summarizes_group_totals(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(module, "console", fake_console)

    module.display_tools_status(
        {
            "core_tools": {"git": True, "fd": False},
            "net_tools": {"curl": True, "wget": True},
        }
    )

    panel = fake_console.printed[0][0]
    assert isinstance(panel, Panel)
    assert "3/4 installed - 75%" in str(panel.title)
    assert str(panel.border_style) == "yellow"
