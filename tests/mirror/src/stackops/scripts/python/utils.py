from __future__ import annotations

import sys
from types import ModuleType

import pytest
import typer
from typer.testing import CliRunner

from stackops.scripts.python import utils as module


def _install_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attrs: dict[str, object]) -> None:
    fake_module = ModuleType(module_name)
    for attr_name, attr_value in attrs.items():
        setattr(fake_module, attr_name, attr_value)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_inspect_utils_help_emojis_delegates_to_devops(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[list[str]] = []
    sentinel = [{"glyph": "⚙"}]

    def fake_emoji_display_diagnostics(glyphs: list[str]) -> list[dict[str, str]]:
        observed.append(glyphs.copy())
        return sentinel

    _install_module(monkeypatch, "stackops.scripts.python.devops", {"emoji_display_diagnostics": fake_emoji_display_diagnostics})

    result = module.inspect_utils_help_emojis()

    assert result == sentinel
    assert observed == [module.UTILS_HELP_GLYPHS]


def test_get_app_help_lists_expected_subapps(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_app = typer.Typer()
    _install_module(monkeypatch, "stackops.scripts.python.helpers.helpers_utils.file_utils_app", {"get_app": lambda: fake_app})
    _install_module(monkeypatch, "stackops.scripts.python.helpers.helpers_utils.machine_utils_app", {"get_app": lambda: fake_app})
    _install_module(monkeypatch, "stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app", {"get_app": lambda: fake_app})
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "machine" in result.stdout
    assert "pyproject" in result.stdout
    assert "file" in result.stdout
