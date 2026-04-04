import asyncio

import pytest

from machineconfig.utils.options_utils.textual_options_form import (
    SelectedOptionMap,
    TextualOptionSpec,
    TextualOptionsFormApp,
)


def test_textual_options_form_submits_selected_values() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "backend": {
            "default": None,
            "options": [None, "cpu", "gpu"],
        },
        "threshold": {
            "default": None,
            "options": [0.5, 1.5],
        },
        "toggle": {
            "default": True,
            "options": [True, 1, False],
        },
    }

    async def run_app() -> SelectedOptionMap | None:
        app = TextualOptionsFormApp(option_specs=option_specs)
        async with app.run_test() as pilot:
            app.set_selection(key="threshold", value=1.5)
            app.set_selection(key="toggle", value=1)
            await pilot.pause()
            await pilot.click("#submit")
            await pilot.pause()
        return app.return_value

    result = asyncio.run(run_app())

    assert result == {
        "backend": None,
        "threshold": 1.5,
        "toggle": 1,
    }


def test_textual_options_form_rejects_missing_default_option() -> None:
    option_specs: dict[str, TextualOptionSpec] = {
        "backend": {
            "default": "gpu",
            "options": ["cpu"],
        },
    }

    with pytest.raises(ValueError, match="default must be present"):
        TextualOptionsFormApp(option_specs=option_specs)

