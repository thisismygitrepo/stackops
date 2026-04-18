from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import stat
from typing import Protocol, cast

import pytest

from stackops.scripts.python.graph.visualize import plotly_browser


class BrowserPathPredicate(Protocol):
    def __call__(self, *, browser_path: Path) -> bool: ...


class RecordingFigure:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, int, int, int, str | None]] = []

    def write_image(self, file: str | Path, *, width: int, height: int, scale: int) -> object:
        self.calls.append((Path(file), width, height, scale, os.environ.get("BROWSER_PATH")))
        return object()


class ExplodingFigure:
    def write_image(self, file: str | Path, *, width: int, height: int, scale: int) -> object:
        _ = file, width, height, scale
        raise ValueError("boom")


def _make_executable_script(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    current_mode = path.stat().st_mode
    path.chmod(current_mode | stat.S_IXUSR)
    return path


def _predicate(name: str) -> BrowserPathPredicate:
    predicate = cast(Callable[..., bool], getattr(plotly_browser, name))

    def wrapped(*, browser_path: Path) -> bool:
        return predicate(browser_path=browser_path)

    return wrapped


def test_resolve_plotly_browser_path_prefers_valid_environment_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable_script(tmp_path.joinpath("chrome"), "#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("BROWSER_PATH", browser_path.as_posix())

    assert plotly_browser.resolve_plotly_browser_path() == browser_path


def test_resolve_plotly_browser_path_rejects_invalid_environment_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = tmp_path.joinpath("missing-chrome")
    monkeypatch.setenv("BROWSER_PATH", browser_path.as_posix())

    with pytest.raises(RuntimeError, match="BROWSER_PATH="):
        plotly_browser.resolve_plotly_browser_path()


def test_is_supported_browser_path_rejects_snap_wrapper(tmp_path: Path) -> None:
    browser_path = _make_executable_script(
        tmp_path.joinpath("chromium"),
        "#!/bin/sh\nexec /snap/bin/chromium \"$@\"\n",
    )
    is_snap_browser_wrapper = _predicate("_is_snap_browser_wrapper")
    is_supported_browser_path = _predicate("_is_supported_browser_path")

    assert is_snap_browser_wrapper(browser_path=browser_path) is True
    assert is_supported_browser_path(browser_path=browser_path) is False


def test_write_plotly_image_sets_browser_path_for_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable_script(tmp_path.joinpath("chrome"), "#!/bin/sh\nexit 0\n")

    def fake_resolve() -> Path:
        return browser_path

    monkeypatch.setenv("BROWSER_PATH", "/tmp/original-browser")
    monkeypatch.setattr(plotly_browser, "resolve_plotly_browser_path", fake_resolve)
    figure = RecordingFigure()
    output_path = tmp_path.joinpath("graph.png")

    plotly_browser.write_plotly_image(fig=figure, output=output_path, width=320, height=180)

    assert figure.calls == [(output_path, 320, 180, 2, browser_path.as_posix())]
    assert os.environ.get("BROWSER_PATH") == "/tmp/original-browser"


def test_write_plotly_image_wraps_export_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable_script(tmp_path.joinpath("chrome"), "#!/bin/sh\nexit 0\n")

    def fake_resolve() -> Path:
        return browser_path

    monkeypatch.setattr(plotly_browser, "resolve_plotly_browser_path", fake_resolve)

    with pytest.raises(RuntimeError, match="Static Plotly export failed"):
        plotly_browser.write_plotly_image(
            fig=ExplodingFigure(),
            output=tmp_path.joinpath("graph.png"),
            width=640,
            height=360,
        )
