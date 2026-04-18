from collections.abc import Callable
import sys
from types import ModuleType

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch
import typer

import stackops.scripts.python.ftpx as target


type FtpxImpl = Callable[[str, str, bool, bool, bool, bool], None]


def _install_ftpx_module(
    monkeypatch: MonkeyPatch,
    *,
    impl: FtpxImpl,
) -> None:
    module = ModuleType(
        "stackops.scripts.python.helpers.helpers_network.ftpx_impl"
    )

    def wrapper(
        *,
        source: str,
        target: str,
        recursive: bool,
        zipFirst: bool,
        cloud: bool,
        overwrite_existing: bool,
    ) -> None:
        impl(source, target, recursive, zipFirst, cloud, overwrite_existing)

    setattr(module, "ftpx", wrapper)
    monkeypatch.setitem(sys.modules, module.__name__, module)


def test_ftpx_passes_all_arguments_to_impl(monkeypatch: MonkeyPatch) -> None:
    seen_calls: list[tuple[str, str, bool, bool, bool, bool]] = []

    def impl(
        source: str,
        target_path: str,
        recursive: bool,
        zip_first: bool,
        cloud: bool,
        overwrite_existing: bool,
    ) -> None:
        seen_calls.append(
            (
                source,
                target_path,
                recursive,
                zip_first,
                cloud,
                overwrite_existing,
            )
        )

    _install_ftpx_module(monkeypatch, impl=impl)

    target.ftpx(
        source="local:/tmp/source",
        target="remote:/tmp/target",
        recursive=True,
        zipFirst=True,
        cloud=True,
        overwrite_existing=True,
    )

    assert seen_calls == [
        (
            "local:/tmp/source",
            "remote:/tmp/target",
            True,
            True,
            True,
            True,
        )
    ]


def test_ftpx_turns_value_errors_into_bad_parameter(
    monkeypatch: MonkeyPatch,
) -> None:
    def impl(
        source: str,
        target_path: str,
        recursive: bool,
        zip_first: bool,
        cloud: bool,
        overwrite_existing: bool,
    ) -> None:
        _ = (
            source,
            target_path,
            recursive,
            zip_first,
            cloud,
            overwrite_existing,
        )
        raise ValueError("bad path syntax")

    _install_ftpx_module(monkeypatch, impl=impl)

    with pytest.raises(typer.BadParameter) as exc_info:
        target.ftpx(
            source="bad",
            target="remote:/tmp/target",
            recursive=False,
            zipFirst=False,
            cloud=False,
            overwrite_existing=False,
        )

    assert "bad path syntax" in str(exc_info.value)


def test_ftpx_marks_missing_source_as_source_parameter(
    monkeypatch: MonkeyPatch,
) -> None:
    def impl(
        source: str,
        target_path: str,
        recursive: bool,
        zip_first: bool,
        cloud: bool,
        overwrite_existing: bool,
    ) -> None:
        _ = (
            source,
            target_path,
            recursive,
            zip_first,
            cloud,
            overwrite_existing,
        )
        raise RuntimeError("SSH Error: source `/tmp/missing` does not exist!")

    _install_ftpx_module(monkeypatch, impl=impl)

    with pytest.raises(typer.BadParameter) as exc_info:
        target.ftpx(
            source="local:/tmp/missing",
            target="remote:/tmp/target",
            recursive=False,
            zipFirst=False,
            cloud=False,
            overwrite_existing=False,
        )

    assert "does not exist!" in str(exc_info.value)
    assert exc_info.value.param_hint == "source"


def test_ftpx_prints_other_runtime_errors_and_exits(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def impl(
        source: str,
        target_path: str,
        recursive: bool,
        zip_first: bool,
        cloud: bool,
        overwrite_existing: bool,
    ) -> None:
        _ = (
            source,
            target_path,
            recursive,
            zip_first,
            cloud,
            overwrite_existing,
        )
        raise RuntimeError("SSH Error: permission denied")

    _install_ftpx_module(monkeypatch, impl=impl)

    with pytest.raises(typer.Exit) as exc_info:
        target.ftpx(
            source="local:/tmp/source",
            target="remote:/tmp/target",
            recursive=False,
            zipFirst=False,
            cloud=False,
            overwrite_existing=False,
        )

    assert exc_info.value.exit_code == 1
    assert "Error: permission denied" in capsys.readouterr().err
