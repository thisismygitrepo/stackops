from typing import Literal, TypeAlias, TypedDict

OptionValue: TypeAlias = str | float | int | bool | None


class TextualSelectOptionSpec(TypedDict):
    kind: Literal["select"]
    default: OptionValue
    options: list[OptionValue]


class TextualTextOptionSpec(TypedDict):
    kind: Literal["text"]
    default: str | None
    allow_blank: bool
    placeholder: str


type TextualOptionSpec = TextualSelectOptionSpec | TextualTextOptionSpec

TextualOptionMap: TypeAlias = dict[str, TextualOptionSpec]
SelectedOptionMap: TypeAlias = dict[str, OptionValue]
