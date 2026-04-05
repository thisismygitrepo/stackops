from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, cast

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Select, Static
from machineconfig.utils.options_utils.textual_options_form_types import OptionValue, SelectedOptionMap, TextualOptionMap

_SELECT_PROMPT: Final[str] = "Choose a value"


@dataclass(frozen=True, slots=True)
class _FieldModel:
    key: str
    select_id: str
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


def _build_field_models(option_specs: TextualOptionMap) -> list[_FieldModel]:
    fields: list[_FieldModel] = []
    for field_index, (key, spec) in enumerate(option_specs.items()):
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
        fields.append(
            _FieldModel(
                key=key,
                select_id=f"""field-{field_index}""",
                select_options=tuple(select_options),
                token_to_value=token_to_value,
                default_token=default_token,
                allow_blank=default_token is None,
            )
        )
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
        self._key_by_select_id = {field.select_id: field.key for field in self._fields}
        self._selected_tokens: dict[str, str | None] = {field.key: field.default_token for field in self._fields}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="shell"):
            yield Static("Set each value, then submit the form.", id="intro")
            with VerticalScroll(id="fields"):
                for field in self._fields:
                    with Vertical(classes="field"):
                        yield Label(field.key, classes="field-label")
                        yield Select(
                            field.select_options,
                            prompt=_SELECT_PROMPT,
                            allow_blank=field.allow_blank,
                            value=field.default_token if field.default_token is not None else Select.NULL,
                            id=field.select_id,
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

    def set_selection(self, key: str, value: OptionValue) -> None:
        field = self._field_by_key[key]
        token = field.token_for_value(value=value)
        self._selected_tokens[key] = token
        select = cast(Select[str], self.query_one(f"""#{field.select_id}""", Select))
        select.value = token

    def _collect_values(self) -> _CollectionResult:
        values: SelectedOptionMap = {}
        for field in self._fields:
            token = self._selected_tokens[field.key]
            if token is None:
                return _CollectionError(message=f"""Field {field.key!r} requires a selection.""")
            values[field.key] = field.value_for_token(token=token)
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
        select_id = event.select.id
        if select_id is None:
            raise RuntimeError("Select widget id is required.")
        key = self._key_by_select_id[select_id]
        self._selected_tokens[key] = _selection_token(value=event.value)
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
