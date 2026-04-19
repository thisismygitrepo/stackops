

import sys
from types import ModuleType

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import seek as module


def _install_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attrs: dict[str, object]) -> None:
    fake_module = ModuleType(module_name)
    for attr_name, attr_value in attrs.items():
        setattr(fake_module, attr_name, attr_value)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_seek_delegates_all_runtime_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_seek(**kwargs: object) -> None:
        calls.append(kwargs)

    _install_module(monkeypatch, "stackops.scripts.python.helpers.helpers_seek.seek_impl", {"seek": fake_seek})

    module.seek(
        path="src",
        search_term="TODO",
        ast=True,
        symantic=True,
        extension=".py",
        file=True,
        dotfiles=True,
        rga=True,
        edit=True,
        install_dependencies=True,
    )

    assert calls == [
        {
            "path": "src",
            "search_term": "TODO",
            "ast": True,
            "symantic": True,
            "extension": ".py",
            "file": True,
            "dotfiles": True,
            "rga": True,
            "edit": True,
            "install_dependencies": True,
        }
    ]


def test_get_app_help_lists_seek_command() -> None:
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "seek" in result.stdout
    assert "seek across files, text matches, and code symbols." in result.stdout
