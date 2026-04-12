from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

import machineconfig.scripts.python.croshell as croshell_module


@dataclass(frozen=True, slots=True)
class Invocation:
    args: tuple[object, ...]
    kwargs: dict[str, object]


def test_croshell_uses_machineconfig_project_path_and_backend_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = tmp_path.joinpath("home")
    project_dir = home_dir.joinpath("code", "machineconfig")
    project_dir.mkdir(parents=True)

    calls: list[Invocation] = []
    fake_module = ModuleType("machineconfig.scripts.python.helpers.helpers_croshell.croshell_impl")

    def fake_croshell(*args: object, **kwargs: object) -> None:
        calls.append(Invocation(args=args, kwargs=dict(kwargs)))

    setattr(fake_module, "croshell", fake_croshell)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_croshell.croshell_impl", fake_module)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    croshell_module.croshell(path="script.py", project_path=None, uv_with="rich", backend="i", profile="dev", machineconfig_project=True, frozen=True)

    assert calls == [
        Invocation(
            args=(),
            kwargs={"path": "script.py", "project_path": str(project_dir), "uv_with": "rich", "backend": "ipython", "profile": "dev", "frozen": True},
        )
    ]


def test_main_delegates_to_typer_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_run(callable_obj: object) -> None:
        calls.append(callable_obj)

    monkeypatch.setattr(croshell_module.typer, "run", fake_run)

    croshell_module.main()

    assert calls == [croshell_module.croshell]
