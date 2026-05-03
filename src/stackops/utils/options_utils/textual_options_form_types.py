from pathlib import Path
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


def resolve_uv_run_config(*, cwd: Path, module_file: Path) -> tuple[list[str], str | None]:
    for probe_path in (cwd, module_file):
        from stackops.utils.accessories import get_repo_root
        repo_root = get_repo_root(probe_path)
        if repo_root is None:
            continue
        if repo_root.joinpath("pyproject.toml").exists():
            return ["textual"], str(repo_root)
    return ["textual", "stackops>=8.98"], None


def use_textual_options_form(
    options: TextualOptionMap,
    *,
    field_label_width_percent: int = 50,
) -> SelectedOptionMap:
    from stackops.utils.accessories import randstr

    random_path = str(Path.home() / "tmp_results" / "textual_options_form" / f"{randstr(6)}.json")

    def func(inputs: "TextualOptionMap", result_path: str, label_width_percent: int) -> None:
        import json
        from stackops.utils.options_utils.textual_options_form import select_option_values_with_textual

        result = select_option_values_with_textual(
            inputs,
            field_label_width_percent=label_width_percent,
        )
        from pathlib import Path

        result_path_obj = Path(result_path)
        result_path_obj.parent.mkdir(parents=True, exist_ok=True)
        result_path_obj.write_text(json.dumps(result, indent=2), encoding="utf-8")

    from stackops.utils.code import run_lambda_function
    uv_with, uv_project_dir = resolve_uv_run_config(cwd=Path.cwd(), module_file=Path(__file__).resolve())
    # uv_with, uv_project_dir = ["textual", "stackops>=8.98"], None
    run_lambda_function(
        lambda: func(
            inputs=options,
            result_path=random_path,
            label_width_percent=field_label_width_percent,
        ),
        uv_with=uv_with,
        uv_project_dir=uv_project_dir,
    )
    import json

    result_content = Path(random_path).read_text(encoding="utf-8")
    result_data = json.loads(result_content)
    from typing import cast

    return cast(SelectedOptionMap, result_data)


if __name__ == "__main__":
    demo_options: TextualOptionMap = {
        "option1": {
            "kind": "select",
            "default": "value1",
            "options": ["value1", "value2", "value3"],
        },
        "option2": {
            "kind": "select",
            "default": 10,
            "options": [10, 20, 30],
        },
        "option3": {
            "kind": "select",
            "default": True,
            "options": [True, False],
        },
        "option4": {
            "kind": "text",
            "default": "hello",
            "allow_blank": False,
            "placeholder": "Enter any string",
        },
    }
    selected_values = use_textual_options_form(demo_options)
    print("Selected values:", selected_values)
