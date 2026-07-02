from collections import Counter
from dataclasses import dataclass
from typing import Literal, NoReturn, overload

import typer

PICKER_PREVIEW_EXTENSION = "md"
PICKER_PREVIEW_SIZE_PERCENT = 60.0


@dataclass(frozen=True)
class InteractivePickerOption[T]:
    value: T
    label: str
    preview: str
    disambiguator: str


def choose_interactive_option[T](
    options: list[InteractivePickerOption[T]], *, missing_tool_message: str, cancelled_message: str, missing_selection_message: str
) -> T:
    option_to_value, option_to_preview = _picker_maps(options)
    selected_label = _select_picker_labels(option_to_preview=option_to_preview, multi=False, missing_tool_message=missing_tool_message)
    if selected_label is None:
        _fail(cancelled_message)

    selected_value = option_to_value.get(selected_label)
    if selected_value is None:
        _fail(f"{missing_selection_message}: {selected_label}")
    return selected_value


def choose_interactive_options[T](options: list[InteractivePickerOption[T]], *, missing_tool_message: str, missing_selection_message: str) -> list[T]:
    option_to_value, option_to_preview = _picker_maps(options)
    selected_labels = _select_picker_labels(option_to_preview=option_to_preview, multi=True, missing_tool_message=missing_tool_message)

    selected_values: list[T] = []
    for selected_label in selected_labels:
        selected_value = option_to_value.get(selected_label)
        if selected_value is None:
            _fail(f"{missing_selection_message}: {selected_label}")
        selected_values.append(selected_value)
    return selected_values


def _picker_maps[T](options: list[InteractivePickerOption[T]]) -> tuple[dict[str, T], dict[str, str]]:
    label_counts = Counter(option.label for option in options)
    option_to_value: dict[str, T] = {}
    option_to_preview: dict[str, str] = {}
    for option in options:
        label = option.label
        if label_counts[label] > 1:
            label = f"{label} [{option.disambiguator}]"
        option_to_value[label] = option.value
        option_to_preview[label] = option.preview
    return option_to_value, option_to_preview


@overload
def _select_picker_labels(*, option_to_preview: dict[str, str], multi: Literal[False], missing_tool_message: str) -> str | None: ...


@overload
def _select_picker_labels(*, option_to_preview: dict[str, str], multi: Literal[True], missing_tool_message: str) -> list[str]: ...


def _select_picker_labels(*, option_to_preview: dict[str, str], multi: bool, missing_tool_message: str) -> str | list[str] | None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    try:
        return choose_from_dict_with_preview(
            options_to_preview_mapping=option_to_preview,
            extension=PICKER_PREVIEW_EXTENSION,
            multi=multi,
            preview_size_percent=PICKER_PREVIEW_SIZE_PERCENT,
        )
    except FileNotFoundError:
        _fail(missing_tool_message)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
