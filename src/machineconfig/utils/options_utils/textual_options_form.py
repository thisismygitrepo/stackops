from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, cast

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from machineconfig.utils.options_utils.textual_options_form_types import (
    OptionValue,
    SelectedOptionMap,
    TextualOptionMap,
    TextualOptionSpec,
)

_SELECT_PROMPT: Final[str] = "Choose a value"
_TEXT_PLACEHOLDER: Final[str] = "Enter a value"


@dataclass(frozen=True, slots=True)
class _SelectFieldModel:
    key: str
    widget_id: str
    select_options: tuple[tuple[str, str], ...]
    token_to_value: dict[str, OptionValue]
    default_token: str | None
    allow_blank: bool

    def token_for_value(self, value: OptionValue) -> str:
        for token, option_value in self.token_to_value.items():
            if _same_option_value(left=option_value, right=value):
                return token
        raise ValueError(f"""Unknown option value for "{self.key}": {value!r}""")

    def value_for_token(self, token: str) -> OptionValue:
        return self.token_to_value[token]


@dataclass(frozen=True, slots=True)
class _TextFieldModel:
    key: str
    widget_id: str
    default_value: str | None
    allow_blank: bool
    placeholder: str


type _FieldModel = _SelectFieldModel | _TextFieldModel


@dataclass(frozen=True, slots=True)
class _CollectedValues:
    values: SelectedOptionMap


@dataclass(frozen=True, slots=True)
class _CollectionError:
    message: str


type _CollectionResult = _CollectedValues | _CollectionError


def _is_supported_option_value(value: object) -> bool:
    return value is None or type(value) in {str, float, int, bool}


def _same_option_value(left: OptionValue, right: OptionValue) -> bool:
    if left is None or right is None:
        return left is right
    return type(left) is type(right) and left == right


def _type_name(value: OptionValue) -> str:
    if value is None:
        return "none"
    return type(value).__name__


def _format_option_label(value: OptionValue) -> str:
    return f"""{value!r} [{_type_name(value)}]"""


def _selection_token(value: object) -> str | None:
    if value == Select.NULL:
        return None
    if not isinstance(value, str):
        raise TypeError(f"""Unexpected select token type: {type(value).__name__}""")
    return value


def _normalized_text_value(value: str) -> str | None:
    if value == "":
        return None
    return value


def _build_select_field_model(*, key: str, field_index: int, spec: TextualOptionSpec) -> _SelectFieldModel:
    if spec["kind"] != "select":
        raise TypeError(f"""Expected select field for "{key}", got {spec["kind"]!r}.""")
    options = spec["options"]
    default = spec["default"]
    if not _is_supported_option_value(value=default):
        raise TypeError(f"""Unsupported default value for "{key}": {default!r}""")
    if len(options) == 0:
        raise ValueError(f"""Field "{key}" must define at least one option.""")
    default_token: str | None = None
    select_options: list[tuple[str, str]] = []
    token_to_value: dict[str, OptionValue] = {}
    for option_index, option in enumerate(options):
        if not _is_supported_option_value(value=option):
            raise TypeError(f"""Unsupported option value for "{key}": {option!r}""")
        token = f"""option-{field_index}-{option_index}"""
        select_options.append((_format_option_label(value=option), token))
        token_to_value[token] = option
        if default_token is None and _same_option_value(left=default, right=option):
            default_token = token
    if default is not None and default_token is None:
        raise ValueError(f"""Field {key!r} default must be present in its options.""")
    return _SelectFieldModel(
        key=key,
        widget_id=f"""field-{field_index}""",
        select_options=tuple(select_options),
        token_to_value=token_to_value,
        default_token=default_token,
        allow_blank=default_token is None,
    )


def _build_text_field_model(*, key: str, field_index: int, spec: TextualOptionSpec) -> _TextFieldModel:
    if spec["kind"] != "text":
        raise TypeError(f"""Expected text field for "{key}", got {spec["kind"]!r}.""")
    default = spec["default"]
    return _TextFieldModel(
        key=key,
        widget_id=f"""field-{field_index}""",
        default_value=default,
        allow_blank=spec["allow_blank"],
        placeholder=spec["placeholder"],
    )


def _build_field_models(option_specs: TextualOptionMap) -> list[_FieldModel]:
    fields: list[_FieldModel] = []
    for field_index, (key, spec) in enumerate(option_specs.items()):
        match spec["kind"]:
            case "select":
                fields.append(_build_select_field_model(key=key, field_index=field_index, spec=spec))
            case "text":
                fields.append(_build_text_field_model(key=key, field_index=field_index, spec=spec))
    return fields


class TextualOptionsFormApp(App[SelectedOptionMap | None]):
    CSS = """
    Screen { background: $surface; }
    Header { background: $primary; color: $text; }
    Footer { background: $panel; }
    #shell { height: 100%; padding: 1 2; }
    #intro { padding-bottom: 1; color: $text-muted; }
    #fields { height: 1fr; border: solid $accent; padding: 1; }
    .field { padding-bottom: 1; }
    .field-label { padding-bottom: 1; color: $text; text-style: bold; }
    Select { width: 1fr; }
    #actions { height: auto; padding-top: 1; align: center middle; }
    #status { width: 1fr; min-height: 3; border: solid $success; padding: 1; }
    #submit { margin-left: 1; }
    """

    BINDINGS = [
        Binding("ctrl+s", "submit", "Submit", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, option_specs: TextualOptionMap) -> None:
        super().__init__()
        self._fields = _build_field_models(option_specs=option_specs)
        self._field_by_key = {field.key: field for field in self._fields}
        self._key_by_widget_id = {field.widget_id: field.key for field in self._fields}
        self._selected_values: dict[str, str | None] = {
            field.key: field.default_token if isinstance(field, _SelectFieldModel) else field.default_value
            for field in self._fields
        }

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="shell"):
            yield Static("Set each value, then submit the form.", id="intro")
            with VerticalScroll(id="fields"):
                for field in self._fields:
                    with Vertical(classes="field"):
                        yield Label(field.key, classes="field-label")
                        if isinstance(field, _SelectFieldModel):
                            yield Select(
                                field.select_options,
                                prompt=_SELECT_PROMPT,
                                allow_blank=field.allow_blank,
                                value=field.default_token if field.default_token is not None else Select.NULL,
                                id=field.widget_id,
                            )
                        else:
                            yield Input(
                                value="" if field.default_value is None else field.default_value,
                                placeholder=field.placeholder or _TEXT_PLACEHOLDER,
                                id=field.widget_id,
                            )
            with Horizontal(id="actions"):
                yield Static("Ready.", id="status")
                yield Button("Submit", id="submit", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Option Values"
        self.sub_title = f"""{len(self._fields)} fields"""

    def _set_status(self, message: str, level: Literal["info", "error", "success"]) -> None:
        color_by_level: dict[Literal["info", "error", "success"], str] = {
            "info": "cyan",
            "error": "red",
            "success": "green",
        }
        color = color_by_level[level]
        self.query_one("#status", Static).update(f"""[{color}]{message}[/{color}]""")

    def set_value(self, key: str, value: OptionValue) -> None:
        field = self._field_by_key[key]
        if isinstance(field, _SelectFieldModel):
            token = field.token_for_value(value=value)
            self._selected_values[key] = token
            select = cast(Select[str], self.query_one(f"""#{field.widget_id}""", Select))
            select.value = token
            return
        if value is not None and not isinstance(value, str):
            raise TypeError(f"""Text field "{key}" only accepts str | None, got {value!r}.""")
        normalized_value = value if value is None else _normalized_text_value(value)
        self._selected_values[key] = normalized_value
        input_widget = self.query_one(f"""#{field.widget_id}""", Input)
        input_widget.value = "" if normalized_value is None else normalized_value

    def set_selection(self, key: str, value: OptionValue) -> None:
        self.set_value(key=key, value=value)

    def _collect_values(self) -> _CollectionResult:
        values: SelectedOptionMap = {}
        for field in self._fields:
            selected_value = self._selected_values[field.key]
            if isinstance(field, _SelectFieldModel):
                if selected_value is None:
                    return _CollectionError(message=f"""Field {field.key!r} requires a selection.""")
                values[field.key] = field.value_for_token(token=selected_value)
                continue
            if selected_value is None and not field.allow_blank:
                return _CollectionError(message=f"""Field {field.key!r} requires a value.""")
            values[field.key] = selected_value
        return _CollectedValues(values=values)

    def action_cancel(self) -> None:
        self.exit(None)

    def action_submit(self) -> None:
        match self._collect_values():
            case _CollectedValues(values=values):
                self._set_status(message="Submitted.", level="success")
                self.exit(values)
            case _CollectionError(message=message):
                self._set_status(message=message, level="error")

    @on(Select.Changed)
    def handle_select_changed(self, event: Select.Changed) -> None:
        widget_id = event.select.id
        if widget_id is None:
            raise RuntimeError("Select widget id is required.")
        key = self._key_by_widget_id[widget_id]
        self._selected_values[key] = _selection_token(value=event.value)
        self._set_status(message=f"""Updated {key!r}.""", level="info")

    @on(Input.Changed)
    def handle_input_changed(self, event: Input.Changed) -> None:
        widget_id = event.input.id
        if widget_id is None:
            raise RuntimeError("Input widget id is required.")
        key = self._key_by_widget_id[widget_id]
        self._selected_values[key] = _normalized_text_value(event.value)
        self._set_status(message=f"""Updated {key!r}.""", level="info")

    @on(Button.Pressed, "#submit")
    def handle_submit_pressed(self, _event: Button.Pressed) -> None:
        self.action_submit()


def select_option_values_with_textual(option_specs: TextualOptionMap) -> SelectedOptionMap:
    if len(option_specs) == 0:
        return {}
    app = TextualOptionsFormApp(option_specs=option_specs)
    result = app.run()
    if result is None:
        raise RuntimeError("Option selection cancelled.")
    return result
