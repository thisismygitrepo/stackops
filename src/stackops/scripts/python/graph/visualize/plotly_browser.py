

from collections.abc import Generator, Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
from typing import Protocol


BROWSER_CANDIDATE_NAMES: tuple[str, ...] = (
    "google-chrome-stable",
    "google-chrome",
    "chrome",
    "chromium",
    "chromium-browser",
)


class PlotlyImageFigure(Protocol):
    def write_image(self, file: str | Path, *, width: int, height: int, scale: int) -> object: ...


def write_plotly_image(
    *,
    fig: PlotlyImageFigure,
    output: Path,
    width: int,
    height: int,
) -> None:
    browser_path = resolve_plotly_browser_path()
    try:
        with _override_browser_path(browser_path=browser_path):
            fig.write_image(output, width=width, height=height, scale=2)
    except Exception as exc:
        raise RuntimeError(
            f"""Static Plotly export failed while launching Chrome/Chromium from '{browser_path}'.
Set BROWSER_PATH to a working non-snap browser binary if you need to override the auto-selected browser."""
        ) from exc


def resolve_plotly_browser_path() -> Path:
    explicit_browser_path = os.environ.get("BROWSER_PATH")
    if explicit_browser_path is not None:
        browser_path = Path(explicit_browser_path).expanduser()
        if _is_supported_browser_path(browser_path=browser_path):
            return browser_path
        raise RuntimeError(
            f"""BROWSER_PATH='{browser_path}' is not a usable non-snap Chrome/Chromium executable.
Plotly static image export requires a real Chrome/Chromium binary, not the snap Chromium launcher."""
        )

    for browser_path in _iter_browser_candidates():
        if _is_supported_browser_path(browser_path=browser_path):
            return browser_path

    return _download_chrome_for_testing()


def _iter_browser_candidates() -> Iterator[Path]:
    seen_paths: set[Path] = set()
    for browser_path in (
        _downloaded_browser_path(browser_root=_plotly_browser_cache_root()),
        _downloaded_browser_path(browser_root=_choreographer_browser_root()),
    ):
        if browser_path is None:
            continue
        resolved_browser_path = browser_path.expanduser()
        if resolved_browser_path in seen_paths:
            continue
        seen_paths.add(resolved_browser_path)
        yield resolved_browser_path

    for browser_name in BROWSER_CANDIDATE_NAMES:
        browser_path_str = shutil.which(browser_name)
        if browser_path_str is None:
            continue
        browser_path = Path(browser_path_str).expanduser()
        if browser_path in seen_paths:
            continue
        seen_paths.add(browser_path)
        yield browser_path


def _download_chrome_for_testing() -> Path:
    from kaleido import get_chrome_sync

    download_root = _plotly_browser_cache_root()
    try:
        browser_path = Path(get_chrome_sync(path=download_root))
    except Exception as exc:
        browser_path = _downloaded_browser_path(browser_root=download_root)
        if browser_path is not None and _is_supported_browser_path(browser_path=browser_path):
            return browser_path
        raise RuntimeError(
            f"""Static Plotly export requires Chrome/Chromium, and no usable browser was found.
Automatic Chrome for Testing download to '{download_root}' failed: {exc}"""
        ) from exc

    if _is_supported_browser_path(browser_path=browser_path):
        return browser_path

    raise RuntimeError(
        f"""Chrome for Testing was downloaded to '{browser_path}', but the resulting binary is not usable.
Set BROWSER_PATH to a working non-snap Chrome/Chromium executable and retry."""
    )


def _plotly_browser_cache_root() -> Path:
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    cache_root = Path(xdg_cache_home).expanduser() if xdg_cache_home else Path.home().joinpath(".cache")
    return cache_root.joinpath("stackops", "plotly-browser")


def _choreographer_browser_root() -> Path:
    from choreographer.cli.defaults import default_download_path

    return Path(default_download_path)


def _downloaded_browser_path(browser_root: Path) -> Path | None:
    relative_browser_path = _downloaded_browser_relative_path()
    if relative_browser_path is None:
        return None
    browser_path = browser_root.joinpath(relative_browser_path)

    if browser_path.exists():
        return browser_path
    return None


def _downloaded_browser_relative_path() -> Path | None:
    from choreographer.cli._cli_utils import get_google_supported_platform_string

    platform_string, _, _, _ = get_google_supported_platform_string()
    if not platform_string:
        return None
    if platform_string.startswith("linux"):
        return Path(rf"chrome-{platform_string}").joinpath("chrome")
    if platform_string.startswith("mac"):
        return Path(rf"chrome-{platform_string}").joinpath(
            "Google Chrome for Testing.app",
            "Contents",
            "MacOS",
            "Google Chrome for Testing",
        )
    if platform_string.startswith("win"):
        return Path(rf"chrome-{platform_string}").joinpath("chrome.exe")
    return None


def _is_supported_browser_path(*, browser_path: Path) -> bool:
    expanded_browser_path = browser_path.expanduser()
    if not expanded_browser_path.is_file():
        return False
    if not os.access(expanded_browser_path, os.X_OK):
        return False

    browser_path_str = str(expanded_browser_path)
    if browser_path_str.startswith("/snap/"):
        return False
    return not _is_snap_browser_wrapper(browser_path=expanded_browser_path)


def _is_snap_browser_wrapper(*, browser_path: Path) -> bool:
    try:
        browser_script = browser_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    except OSError:
        return False
    return "/snap/bin/chromium" in browser_script


@contextmanager
def _override_browser_path(*, browser_path: Path) -> Generator[None, None, None]:
    previous_browser_path = os.environ.get("BROWSER_PATH")
    os.environ["BROWSER_PATH"] = str(browser_path)
    try:
        yield
    finally:
        if previous_browser_path is None:
            os.environ.pop("BROWSER_PATH", None)
        else:
            os.environ["BROWSER_PATH"] = previous_browser_path
