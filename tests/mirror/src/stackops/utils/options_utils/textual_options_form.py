

from typing import Literal

import pytest

import stackops.utils.options_utils.textual_options_form as textual_options_form
from stackops.utils.options_utils.textual_options_form_types import (
    SelectedOptionMap,
    TextualOptionMap,
    TextualSelectOptionSpec,
)


def test_build_select_field_model_treats_bool_and_int_as_distinct_values() -> None:
    spec: TextualSelectOptionSpec = {
        "kind": "select",
        "default": True,
        "options": [1, True],
    }

    model = textual_options_form._build_select_field_model(
        key="flag",
        field_index=2,
        spec=spec,
    )

    assert model.default_token == "option-2-1"
    assert model.value_for_token("option-2-0") == 1
    assert model.value_for_token("option-2-1") is True


def test_selection_token_rejects_non_string_values() -> None:
    with pytest.raises(TypeError):
        textual_options_form._selection_token(3.14)


def test_collect_values_reports_missing_required_text() -> None:
    option_specs: TextualOptionMap = {
        "name": {
            "kind": "text",
            "default": None,
            "allow_blank": False,
            "placeholder": "",
        }
    }

    app = textual_options_form.TextualOptionsFormApp(option_specs)
    result = app._collect_values()

    assert isinstance(result, textual_options_form._CollectionError)
    assert result.message == "Field 'name' requires a value."


def test_action_submit_exits_with_selected_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    option_specs: TextualOptionMap = {
        "choice": {
            "kind": "select",
            "default": "alpha",
            "options": ["alpha", "beta"],
        },
        "note": {
            "kind": "text",
            "default": "hello",
            "allow_blank": False,
            "placeholder": "",
        },
    }

    app = textual_options_form.TextualOptionsFormApp(option_specs)
    statuses: list[tuple[str, Literal["info", "error", "success"]]] = []
    exits: list[SelectedOptionMap] = []

    def fake_set_status(message: str, level: Literal["info", "error", "success"]) -> None:
        statuses.append((message, level))

    def fake_exit(result: SelectedOptionMap) -> None:
        exits.append(result)

    monkeypatch.setattr(app, "_set_status", fake_set_status)
    monkeypatch.setattr(app, "exit", fake_exit)

    app.action_submit()

    assert statuses == [("Submitted.", "success")]
    assert exits == [{"choice": "alpha", "note": "hello"}]
