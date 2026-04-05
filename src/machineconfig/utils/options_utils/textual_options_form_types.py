from typing import TypeAlias, TypedDict


OptionValue: TypeAlias = str | float | int | bool | None


class TextualOptionSpec(TypedDict):
    default: OptionValue
    options: list[OptionValue]


TextualOptionMap: TypeAlias = dict[str, TextualOptionSpec]
SelectedOptionMap: TypeAlias = dict[str, OptionValue]


def use_textual_options_form(options: TextualOptionMap, ) -> "SelectedOptionMap":
    from pathlib import Path
    from machineconfig.utils.accessories import randstr
    random_path = str(Path.home() / "tmp_results" / "textual_options_form" / f"{randstr(6)}.json")

    def func(inputs: "TextualOptionMap", result_path: str) -> None:
        from machineconfig.utils.options_utils.textual_options_form import select_option_values_with_textual
        result = select_option_values_with_textual(inputs, )
        from pathlib import Path
        result_path_obj = Path(result_path)
        result_path_obj.parent.mkdir(parents=True, exist_ok=True)
        import json
        result_path_obj.write_text(json.dumps(result, indent=2), encoding="utf-8")

    from machineconfig.utils.code import run_lambda_function
    run_lambda_function(
        lambda : func(inputs=options, result_path=random_path),
        uv_with=["textual", "machineconfig>=8.89"],
        uv_project_dir=None,
    )
    import json
    result_content = Path(random_path).read_text(encoding="utf-8")
    result_data = json.loads(result_content)
    from typing import cast
    return cast(SelectedOptionMap, result_data)


if __name__ == "__main__":
    demo_options: TextualOptionMap = {
        "option1": {
            "default": "value1",
            "options": ["value1", "value2", "value3"],
        },
        "option2": {
            "default": 10,
            "options": [10, 20, 30],
        },
        "option3": {
            "default": True,
            "options": [True, False],
        },
    }
    selected_values = use_textual_options_form(demo_options)
    print("Selected values:", selected_values)