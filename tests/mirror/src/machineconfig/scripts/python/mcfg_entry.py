from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

from machineconfig.scripts.python import mcfg_entry as module


def _install_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attrs: dict[str, object]) -> None:
    fake_module = ModuleType(module_name)
    for attr_name, attr_value in attrs.items():
        setattr(fake_module, attr_name, attr_value)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_fire_forwards_runtime_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_fire(**kwargs: object) -> None:
        calls.append(kwargs)

    _install_module(monkeypatch, "machineconfig.scripts.python.fire_jobs", {"fire": fake_fire})
    ctx = cast(typer.Context, SimpleNamespace(args=[]))

    module.fire(
        ctx=ctx,
        path="job.py",
        function="run",
        ve=".venv",
        cmd=True,
        debug=True,
        choose_function=True,
        loop=True,
        interactive=True,
        jupyter=True,
        marimo=True,
        streamlit=True,
        module=True,
        script=True,
        optimized=True,
        zellij_tab="jobs",
        submit_to_cloud=True,
        root_repo=True,
        remote=True,
        environment="lab",
        holdDirectory=True,
        PathExport=True,
        git_pull=True,
        watch=True,
    )

    assert len(calls) == 1
    call = calls[0]
    assert call["ctx"] is ctx
    assert call["path"] == "job.py"
    assert call["function"] == "run"
    assert call["ve"] == ".venv"
    assert call["interactive"] is True
    assert call["marimo"] is True
    assert call["streamlit"] is True
    assert call["submit_to_cloud"] is True
    assert call["environment"] == "lab"
    assert call["watch"] is True


def test_croshell_maps_backend_and_forwards_args(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_croshell(**kwargs: object) -> None:
        calls.append(kwargs)

    _install_module(monkeypatch, "machineconfig.scripts.python.croshell", {"croshell": fake_croshell})
    backend_loose = "ipython"

    module.croshell(path="demo.py", project_path="/tmp/proj", uv_with="rich", backend=backend_loose, profile="dev")

    assert calls == [
        {"path": "demo.py", "project_path": "/tmp/proj", "uv_with": "rich", "backend": module.BACKENDS_MAP[backend_loose], "profile": "dev"}
    ]


@pytest.mark.parametrize(
    ("wrapper_name", "module_name"),
    [
        ("devops", "machineconfig.scripts.python.devops"),
        ("cloud", "machineconfig.scripts.python.cloud"),
        ("terminal", "machineconfig.scripts.python.terminal"),
        ("agents", "machineconfig.scripts.python.agents"),
        ("utils", "machineconfig.scripts.python.utils"),
        ("seek", "machineconfig.scripts.python.seek"),
    ],
)
def test_context_wrappers_forward_ctx_args(monkeypatch: pytest.MonkeyPatch, wrapper_name: str, module_name: str) -> None:
    calls: list[tuple[list[str], bool]] = []

    class FakeApp:
        def __call__(self, args: list[str], *, standalone_mode: bool) -> None:
            calls.append((args.copy(), standalone_mode))

    _install_module(monkeypatch, module_name, {"get_app": lambda: FakeApp()})
    ctx = cast(typer.Context, SimpleNamespace(args=["--help"]))

    getattr(module, wrapper_name)(ctx)

    assert calls == [(["--help"], False)]


def test_get_app_help_lists_top_level_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "devops" in result.stdout
    assert "cloud" in result.stdout
    assert "terminal" in result.stdout
    assert "agents" in result.stdout
    assert "utils" in result.stdout
    assert "seek" in result.stdout
    assert "fire" in result.stdout
    assert "croshell" in result.stdout
