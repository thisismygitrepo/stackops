from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_sessions import sessions_layout_source as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def make_context(help_text: str) -> typer.Context:
    return cast(typer.Context, SimpleNamespace(get_help=lambda: help_text))


def test_resolve_layout_source_uses_generated_test_layouts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    generated_layouts: list[LayoutConfig] = [
        {"layoutName": "alpha", "layoutTabs": []},
        {"layoutName": "beta", "layoutTabs": []},
    ]
    monkeypatch.setattr(subject, "build_test_layouts", lambda base_dir: generated_layouts)
    monkeypatch.setattr(subject, "count_tabs_in_layouts", lambda layouts: 5)

    layout_source = subject.resolve_layout_source(
        ctx=make_context("HELP"),
        layouts_file=None,
        test_layout=True,
    )

    assert layout_source == subject.LayoutSource(
        source_label="generated test layout",
        all_layouts=generated_layouts,
        is_test_layout=True,
    )
    assert "Using generated test layout with 2 layouts and 5 tabs." in capsys.readouterr().out


def test_resolve_layout_source_rejects_mixed_sources() -> None:
    with pytest.raises(ValueError, match="cannot be used together"):
        subject.resolve_layout_source(
            ctx=make_context("HELP"),
            layouts_file="layouts.json",
            test_layout=True,
        )


def test_resolve_layouts_file_path_missing_shows_help_and_exits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolve_layouts_file_path = cast(
        Callable[[typer.Context, str | None], Path],
        getattr(subject, "_resolve_layouts_file_path"),
    )
    monkeypatch.setattr(subject.Path, "home", lambda: tmp_path)

    with pytest.raises(typer.Exit) as exc_info:
        resolve_layouts_file_path(
            ctx=make_context("HELP TEXT"),
            layouts_file=None,
        )

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "HELP TEXT" in captured.out
    assert f"Layouts file not found: {tmp_path / 'dotfiles' / 'machineconfig' / 'layouts.json'}" in captured.err


def test_load_selected_layouts_and_choose_tabs_clone_and_filter() -> None:
    layout_source = subject.LayoutSource(
        source_label="layouts.json",
        all_layouts=[
            {
                "layoutName": "Alpha",
                "layoutTabs": [
                    {"tabName": "tab-1", "startDir": ".", "command": "echo alpha"},
                ],
            },
            {
                "layoutName": "Beta",
                "layoutTabs": [
                    {"tabName": "tab-1", "startDir": ".", "command": "echo beta-1"},
                    {"tabName": "tab-2", "startDir": ".", "command": "echo beta-2"},
                ],
            },
        ],
        is_test_layout=False,
    )

    selected_layouts = subject.load_selected_layouts_from_source(
        layout_source=layout_source,
        choose_layouts="alpha",
    )
    selected_layouts[0]["layoutTabs"][0]["command"] = "changed"

    assert [layout["layoutName"] for layout in selected_layouts] == ["Alpha"]
    assert layout_source.all_layouts[0]["layoutTabs"][0]["command"] == "echo alpha"

    custom_layouts = subject.choose_tabs_from_source(
        layout_source=layout_source,
        layouts_selected=[layout_source.all_layouts[1]],
        choose_tabs="tab-1,Beta::tab-2",
    )

    assert custom_layouts == [
        {
            "layoutName": "custom-tabs",
            "layoutTabs": [
                {"tabName": "tab-1", "startDir": ".", "command": "echo beta-1"},
                {"tabName": "tab-2", "startDir": ".", "command": "echo beta-2"},
            ],
        }
    ]

    with pytest.raises(ValueError, match="matched no tabs"):
        subject.choose_tabs_from_source(
            layout_source=layout_source,
            layouts_selected=[layout_source.all_layouts[1]],
            choose_tabs="missing-tab",
        )
