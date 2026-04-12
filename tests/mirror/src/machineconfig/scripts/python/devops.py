from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

import machineconfig.scripts.python.devops as devops_module


@dataclass(frozen=True, slots=True)
class Invocation:
    args: tuple[object, ...]
    kwargs: dict[str, object]


def _register_callable_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attr_name: str, calls: list[Invocation]) -> None:
    fake_module = ModuleType(module_name)

    def fake_callable(*args: object, **kwargs: object) -> None:
        calls.append(Invocation(args=args, kwargs=dict(kwargs)))

    setattr(fake_module, attr_name, fake_callable)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def _register_get_app_module(monkeypatch: pytest.MonkeyPatch, module_name: str, calls: list[Invocation]) -> None:
    fake_module = ModuleType(module_name)

    def get_app() -> Callable[..., object]:
        def fake_app(*args: object, **kwargs: object) -> None:
            calls.append(Invocation(args=args, kwargs=dict(kwargs)))

        return fake_app

    setattr(fake_module, "get_app", get_app)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_emoji_display_diagnostics_reports_width_and_variation_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_wcwidth = ModuleType("wcwidth")
    setattr(fake_wcwidth, "wcswidth", lambda _value: 2)
    monkeypatch.setitem(sys.modules, "wcwidth", fake_wcwidth)

    diagnostics = devops_module.emoji_display_diagnostics(["🛠️"])
    diagnostic = diagnostics[0]

    assert diagnostic["emoji"] == "🛠️"
    assert diagnostic["char_count"] == 2
    assert diagnostic["has_variation_selector_16"] is True
    assert diagnostic["terminal_width"] == 2
    assert diagnostic["codepoints"][0].startswith("U+1F6E0 ")
    assert diagnostic["codepoints"][1] == "U+FE0F VARIATION SELECTOR-16"


def test_inspect_devops_help_emojis_returns_expected_emoji_sequence() -> None:
    diagnostics = devops_module.inspect_devops_help_emojis()

    assert [item["emoji"] for item in diagnostics] == ["🔧", "📁", "🔩", "💾", "🔧", "🌐", "🚀"]


def test_install_lazy_loads_installer_cli_and_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Invocation] = []
    _register_callable_module(monkeypatch, "machineconfig.utils.installer_utils.installer_cli", "main_installer_cli", calls)

    devops_module.install(which="fd,rg", group=False, interactive=True, update=True, version="latest")

    assert calls == [Invocation(args=(), kwargs={"which": "fd,rg", "group": False, "interactive": True, "update": True, "version": "latest"})]


@pytest.mark.parametrize(
    ("callable_name", "module_name"),
    [
        ("repos", "machineconfig.scripts.python.helpers.helpers_devops.cli_repos"),
        ("config", "machineconfig.scripts.python.helpers.helpers_devops.cli_config"),
        ("data", "machineconfig.scripts.python.helpers.helpers_devops.cli_data"),
        ("self_cmd", "machineconfig.scripts.python.helpers.helpers_devops.cli_self"),
        ("network", "machineconfig.scripts.python.helpers.helpers_devops.cli_nw"),
    ],
)
def test_context_commands_forward_context_args(monkeypatch: pytest.MonkeyPatch, callable_name: str, module_name: str) -> None:
    calls: list[Invocation] = []
    _register_get_app_module(monkeypatch, module_name, calls)

    context = cast(typer.Context, SimpleNamespace(args=["--flag", "value"]))
    command = getattr(devops_module, callable_name)
    command(context)

    assert calls == [Invocation(args=(["--flag", "value"],), kwargs={"standalone_mode": False})]


def test_execute_lazy_loads_script_runner_and_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Invocation] = []
    _register_callable_module(monkeypatch, "machineconfig.scripts.python.helpers.helpers_devops.run_script", "run_py_script", calls)

    context = cast(typer.Context, SimpleNamespace(args=[]))

    devops_module.execute(ctx=context, name="build", where="custom", interactive=True, command=True, list_scripts=False)

    assert calls == [
        Invocation(args=(), kwargs={"ctx": context, "name": "build", "where": "custom", "interactive": True, "command": True, "list_scripts": False})
    ]


def test_get_app_help_lists_top_level_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(devops_module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "install" in result.stdout
    assert "repos" in result.stdout
    assert "config" in result.stdout
    assert "data" in result.stdout
    assert "self" in result.stdout
    assert "network" in result.stdout
    assert "execute" in result.stdout
