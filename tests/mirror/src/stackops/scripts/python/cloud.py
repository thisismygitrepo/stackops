from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType

import pytest
from typer.testing import CliRunner

import stackops.scripts.python.cloud as cloud_module


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


def test_get_app_help_lists_top_level_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(cloud_module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "sync" in result.stdout
    assert "copy" in result.stdout
    assert "mount" in result.stdout
    assert "ftpx" in result.stdout


def test_sync_lazy_loads_helper_and_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Invocation] = []
    _register_callable_module(monkeypatch, "stackops.scripts.python.helpers.helpers_cloud.cloud_sync", "main", calls)

    cloud_module.sync(
        source="local",
        target="remote",
        config="cloud.yaml",
        transfers=3,
        root="root",
        key="key",
        pwd="pwd",
        encrypt=True,
        zip_=True,
        bisync=True,
        delete=False,
        verbose=True,
    )

    assert calls == [
        Invocation(
            args=(),
            kwargs={
                "source": "local",
                "target": "remote",
                "config": "cloud.yaml",
                "transfers": 3,
                "root": "root",
                "key": "key",
                "pwd": "pwd",
                "encrypt": True,
                "zip_": True,
                "bisync": True,
                "delete": False,
                "verbose": True,
            },
        )
    ]


def test_copy_lazy_loads_helper_and_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Invocation] = []
    _register_callable_module(monkeypatch, "stackops.scripts.python.helpers.helpers_cloud.cloud_copy", "main", calls)

    cloud_module.copy(
        source="from",
        target="to",
        overwrite=True,
        share=False,
        rel2home=True,
        root="root",
        key="key",
        pwd="pwd",
        encrypt=False,
        zip_=True,
        os_specific=True,
        config="cloud.yaml",
    )

    assert calls == [
        Invocation(
            args=(),
            kwargs={
                "source": "from",
                "target": "to",
                "overwrite": True,
                "share": False,
                "rel2home": True,
                "root": "root",
                "key": "key",
                "pwd": "pwd",
                "encrypt": False,
                "zip_": True,
                "os_specific": True,
                "config": "cloud.yaml",
            },
        )
    ]


def test_mount_lazy_loads_helper_and_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Invocation] = []
    _register_callable_module(monkeypatch, "stackops.scripts.python.helpers.helpers_cloud.cloud_mount", "mount", calls)

    cloud_module.mount(cloud="drive", destination="/mnt/drive", network="network-drive", backend="tmux", interactive=False)

    assert calls == [
        Invocation(
            args=(), kwargs={"cloud": "drive", "destination": "/mnt/drive", "network": "network-drive", "backend": "tmux", "interactive": False}
        )
    ]


def test_ftpx_lazy_loads_helper_and_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Invocation] = []
    _register_callable_module(monkeypatch, "stackops.scripts.python.ftpx", "ftpx", calls)

    cloud_module.ftpx(
        source="machine-a:/tmp/source", target="machine-b:/tmp/target", recursive=True, zipFirst=True, cloud=True, overwrite_existing=True
    )

    assert calls == [
        Invocation(
            args=(),
            kwargs={
                "source": "machine-a:/tmp/source",
                "target": "machine-b:/tmp/target",
                "recursive": True,
                "zipFirst": True,
                "cloud": True,
                "overwrite_existing": True,
            },
        )
    ]
