import asyncio
from pathlib import Path

import pytest

import machineconfig.utils.accessories as accessories
import machineconfig.utils.options_utils.textual_options_form_types as textual_options_form_types
from machineconfig.utils.options_utils.textual_options_form import (
    SelectedOptionMap,
    TextualOptionSpec,
    TextualOptionsFormApp,
)
from textual.widgets import Input, Label


def test_textual_options_form_submits_selected_values() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "backend": {
            "kind": "select",
            "default": None,
            "options": [None, "cpu", "gpu"],
        },
        "threshold": {
            "kind": "select",
            "default": None,
            "options": [0.5, 1.5],
        },
        "toggle": {
            "kind": "select",
            "default": True,
            "options": [True, 1, False],
        },
        "notes": {
            "kind": "text",
            "default": "keep me",
            "allow_blank": False,
            "placeholder": "Enter any string",
        },
    }

    async def run_app() -> SelectedOptionMap | None:
        app = TextualOptionsFormApp(option_specs=option_specs)
        async with app.run_test() as pilot:
            app.set_value(key="threshold", value=1.5)
            app.set_value(key="toggle", value=1)
            app.set_value(key="notes", value="custom text")
            await pilot.pause()
            await pilot.click("#submit")
            await pilot.pause()
        return app.return_value

    result = asyncio.run(run_app())

    assert result == {
        "backend": None,
        "threshold": 1.5,
        "toggle": 1,
        "notes": "custom text",
    }


def test_textual_options_form_allows_blank_text_when_configured() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "notes": {
            "kind": "text",
            "default": None,
            "allow_blank": True,
            "placeholder": "Optional text",
        },
    }

    async def run_app() -> SelectedOptionMap | None:
        app = TextualOptionsFormApp(option_specs=option_specs)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#submit")
            await pilot.pause()
        return app.return_value

    result = asyncio.run(run_app())

    assert result == {"notes": None}


def test_textual_options_form_rejects_blank_required_text() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "notes": {
            "kind": "text",
            "default": None,
            "allow_blank": False,
            "placeholder": "Required text",
        },
    }

    async def run_app() -> SelectedOptionMap | None:
        app = TextualOptionsFormApp(option_specs=option_specs)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#submit")
            await pilot.pause()
        return app.return_value

    result = asyncio.run(run_app())

    assert result is None


def test_textual_options_form_rejects_missing_default_option() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "backend": {
            "kind": "select",
            "default": "gpu",
            "options": ["cpu"],
        },
    }

    with pytest.raises(ValueError, match="default must be present"):
        TextualOptionsFormApp(option_specs=option_specs)


def test_textual_options_form_applies_custom_field_label_width_percent() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "notes": {
            "kind": "text",
            "default": "hello",
            "allow_blank": False,
            "placeholder": "Enter any string",
        },
    }

    async def run_app() -> tuple[float, float]:
        app = TextualOptionsFormApp(option_specs=option_specs, field_label_width_percent=35)
        async with app.run_test() as pilot:
            await pilot.pause()
            label_width_style = app.query_one(".field-label", Label).styles.width
            input_width_style = app.query_one(".field-control", Input).styles.width
            assert label_width_style is not None
            assert input_width_style is not None
            label_width = label_width_style.value
            input_width = input_width_style.value
        return label_width, input_width

    label_width, input_width = asyncio.run(run_app())

    assert label_width == 35
    assert input_width == 65


def test_textual_options_form_rejects_invalid_field_label_width_percent() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "notes": {
            "kind": "text",
            "default": "hello",
            "allow_blank": False,
            "placeholder": "Enter any string",
        },
    }

    with pytest.raises(ValueError, match="between 1 and 99"):
        TextualOptionsFormApp(option_specs=option_specs, field_label_width_percent=0)


def test_resolve_uv_run_config_prefers_repo_root_from_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path("/tmp/repo")

    def fake_get_repo_root(path: Path) -> Path | None:
        if path == Path("/worktree/current"):
            return repo_root
        return None

    monkeypatch.setattr(accessories, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(Path, "exists", lambda self: self == repo_root / "pyproject.toml")

    uv_with, uv_project_dir = textual_options_form_types.resolve_uv_run_config(
        cwd=Path("/worktree/current"),
        module_file=Path("/site-packages/machineconfig/textual_options_form_types.py"),
    )

    assert uv_with == ["textual"]
    assert uv_project_dir == str(repo_root)


def test_resolve_uv_run_config_falls_back_to_published_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(accessories, "get_repo_root", lambda _path: None)

    uv_with, uv_project_dir = textual_options_form_types.resolve_uv_run_config(
        cwd=Path("/tmp"),
        module_file=Path("/site-packages/machineconfig/textual_options_form_types.py"),
    )

    assert uv_with == ["textual", "machineconfig>=8.90"]
    assert uv_project_dir is None
