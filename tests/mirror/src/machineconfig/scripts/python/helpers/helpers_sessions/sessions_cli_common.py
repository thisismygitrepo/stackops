from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import typer

import machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_common as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


class StubContext:
    def get_help(self) -> str:
        return "HELP"


def _make_context() -> typer.Context:
    return cast(typer.Context, StubContext())


def test_resolve_layouts_file_returns_existing_explicit_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layouts_file = tmp_path.joinpath("layouts.json")
    layouts_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(subject, "find_layout_file", lambda *, layout_path: str(layouts_file))

    resolved = subject.resolve_layouts_file(_make_context(), "custom.json")

    assert resolved == layouts_file


def test_resolve_layouts_file_missing_emits_help_and_exits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path.joinpath("missing.json")
    monkeypatch.setattr(subject, "find_layout_file", lambda *, layout_path: str(missing))

    with pytest.raises(typer.Exit) as exc_info:
        subject.resolve_layouts_file(_make_context(), "custom.json")

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "HELP" in captured.out
    assert str(missing) in captured.err


@pytest.mark.parametrize(
    ("choose_layouts", "expected_names", "interactive"), [(None, [], False), ("", [], True), ("api, web", ["api", "web"], False)]
)
def test_load_selected_layouts_parses_selector_modes(
    choose_layouts: str | None, expected_names: list[str], interactive: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_select_layout(*, layouts_json_file: str, selected_layouts_names: list[str], select_interactively: bool) -> list[LayoutConfig]:
        captured["layouts_json_file"] = layouts_json_file
        captured["selected_layouts_names"] = selected_layouts_names
        captured["select_interactively"] = select_interactively
        return []

    monkeypatch.setattr(subject, "select_layout", fake_select_layout)

    subject.load_selected_layouts(Path("/tmp/layouts.json"), choose_layouts)

    assert captured == {"layouts_json_file": "/tmp/layouts.json", "selected_layouts_names": expected_names, "select_interactively": interactive}


def test_choose_tabs_from_layouts_selects_allowed_tabs_only(monkeypatch: pytest.MonkeyPatch) -> None:
    alpha_shared: TabConfig = {"tabName": "shared", "startDir": "/a", "command": "echo a"}
    alpha_only: TabConfig = {"tabName": "alpha-only", "startDir": "/a2", "command": "echo a2"}
    beta_build: TabConfig = {"tabName": "build", "startDir": "/b", "command": "echo b"}
    gamma_shared: TabConfig = {"tabName": "shared", "startDir": "/g", "command": "echo g"}
    layouts_selected: list[LayoutConfig] = [
        {"layoutName": "alpha", "layoutTabs": [alpha_shared, alpha_only]},
        {"layoutName": "beta", "layoutTabs": [beta_build]},
    ]
    all_layouts: list[LayoutConfig] = [
        {"layoutName": "alpha", "layoutTabs": [alpha_shared, alpha_only]},
        {"layoutName": "beta", "layoutTabs": [beta_build]},
        {"layoutName": "gamma", "layoutTabs": [gamma_shared]},
    ]
    monkeypatch.setattr(subject, "load_all_layouts", lambda layouts_file_resolved: all_layouts)

    selected = subject.choose_tabs_from_layouts(Path("/tmp/layouts.json"), layouts_selected, "shared,beta::build")

    assert selected == [{"layoutName": "custom-tabs", "layoutTabs": [alpha_shared, beta_build]}]


def test_choose_tabs_from_layouts_rejects_unknown_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    layouts_selected: list[LayoutConfig] = [{"layoutName": "alpha", "layoutTabs": [{"tabName": "shared", "startDir": "/a", "command": "echo a"}]}]
    monkeypatch.setattr(subject, "load_all_layouts", lambda layouts_file_resolved: layouts_selected)

    with pytest.raises(ValueError, match="matched no tabs"):
        subject.choose_tabs_from_layouts(Path("/tmp/layouts.json"), layouts_selected, "missing")


def test_substitute_home_in_layouts_preserves_layout_names(monkeypatch: pytest.MonkeyPatch) -> None:
    layouts_selected: list[LayoutConfig] = [{"layoutName": "alpha", "layoutTabs": [{"tabName": "shared", "startDir": "~", "command": "echo a"}]}]

    def fake_substitute_home(*, tabs: list[TabConfig]) -> list[TabConfig]:
        return [{"tabName": tab["tabName"], "startDir": f"/resolved/{index}", "command": tab["command"]} for index, tab in enumerate(tabs)]

    monkeypatch.setattr(subject, "substitute_home", fake_substitute_home)

    substituted = subject.substitute_home_in_layouts(layouts_selected)

    assert substituted == [{"layoutName": "alpha", "layoutTabs": [{"tabName": "shared", "startDir": "/resolved/0", "command": "echo a"}]}]


def test_resolve_standard_backend_returns_auto_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject.platform, "system", lambda: "Linux")

    assert subject.resolve_standard_backend("auto") == "zellij"


def test_resolve_standard_backend_rejects_tmux_on_windows(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(subject.platform, "system", lambda: "Windows")

    with pytest.raises(typer.Exit) as exc_info:
        subject.resolve_standard_backend("tmux")

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "tmux is not supported on Windows" in captured.err
