import os
from pathlib import Path
import stat

import pytest

from machineconfig.scripts.python.graph.visualize import plotly_browser


def _make_executable(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_resolve_plotly_browser_path_prefers_explicit_browser_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable(tmp_path.joinpath("chrome"), "#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("BROWSER_PATH", str(browser_path))

    assert plotly_browser.resolve_plotly_browser_path() == browser_path


def test_resolve_plotly_browser_path_rejects_snap_wrapper_browser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable(
        tmp_path.joinpath("chromium-browser"),
        "#!/bin/sh\nexec /snap/bin/chromium \"$@\"\n",
    )
    monkeypatch.setenv("BROWSER_PATH", str(browser_path))

    with pytest.raises(RuntimeError, match="non-snap Chrome/Chromium"):
        plotly_browser.resolve_plotly_browser_path()


def test_resolve_plotly_browser_path_downloads_browser_when_needed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable(tmp_path.joinpath("chrome"), "#!/bin/sh\nexit 0\n")
    monkeypatch.delenv("BROWSER_PATH", raising=False)
    monkeypatch.setattr(plotly_browser, "_iter_browser_candidates", lambda: iter(()))
    monkeypatch.setattr(plotly_browser, "_download_chrome_for_testing", lambda: browser_path)

    assert plotly_browser.resolve_plotly_browser_path() == browser_path


def test_write_plotly_image_sets_browser_path_for_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    browser_path = _make_executable(tmp_path.joinpath("chrome"), "#!/bin/sh\nexit 0\n")
    monkeypatch.setattr(plotly_browser, "resolve_plotly_browser_path", lambda: browser_path)
    monkeypatch.setenv("BROWSER_PATH", "/existing/browser")

    figure = _FakeFigure()
    output_path = tmp_path.joinpath("out.png")

    plotly_browser.write_plotly_image(fig=figure, output=output_path, width=123, height=456)

    assert figure.calls == [(output_path, 123, 456, 2, str(browser_path))]
    assert os.environ["BROWSER_PATH"] == "/existing/browser"


class _FakeFigure:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, int, int, int, str | None]] = []

    def write_image(self, file: str | Path, *, width: int, height: int, scale: int) -> None:
        self.calls.append((Path(file), width, height, scale, os.environ.get("BROWSER_PATH")))
