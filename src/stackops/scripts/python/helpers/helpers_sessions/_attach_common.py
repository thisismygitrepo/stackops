import re
import shlex
import subprocess
from pathlib import Path
from typing import Literal, TypeAlias, overload

import stackops.settings.zellij.layouts as layouts
from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.options_utils.options import choose_from_options
from stackops.utils.path_reference import get_path_reference_path

STANDARD = get_path_reference_path(module=layouts, path_reference=layouts.ST2_PATH_REFERENCE)
NEW_SESSION_LABEL = "NEW SESSION"
KILL_ALL_AND_NEW_LABEL = "KILL ALL SESSIONS & START NEW"
_ANSI_ESCAPE_RE = re.compile(
    r"(?:\x1B|\u001B|\033)\[[0-?]*[ -/]*[@-~]|\[[0-9;?]+[ -/]*[@-~]|\[m"
)

AttachSessionAction: TypeAlias = Literal["error", "handoff_script"]
AttachSessionChoice: TypeAlias = tuple[AttachSessionAction, str]


def collect_selected_option_scripts(
    selections: list[str],
    options_to_script: dict[str, str],
    option_parent_labels: dict[str, tuple[str, ...]],
) -> tuple[list[str], str | None]:
    selected_labels = tuple(dict.fromkeys(selections))
    selected_label_set = set(selected_labels)
    scripts: list[str] = []
    for selection in selected_labels:
        script = options_to_script.get(selection)
        if script is None:
            return [], selection
        parent_labels = option_parent_labels.get(selection, ())
        if any(parent_label in selected_label_set for parent_label in parent_labels):
            continue
        scripts.append(script)
    return scripts, None


def strip_ansi_codes(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def natural_sort_key(text: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def run_command(args: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def quote(value: str | Path) -> str:
    return shlex.quote(str(value))


@overload
def interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
    multi: Literal[False] = False,
) -> str | None: ...


@overload
def interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
    multi: Literal[True],
) -> list[str]: ...


def interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
    multi: bool = False,
) -> str | list[str] | None:
    if len(options_to_preview_mapping) == 0:
        raise RuntimeError("No options available.")
    if check_tool_exists("tv"):
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

        try:
            if multi:
                chosen_multi = choose_from_dict_with_preview(
                    options_to_preview_mapping=options_to_preview_mapping,
                    extension="md",
                    multi=True,
                    preview_size_percent=70.0,
                )
                return chosen_multi
            return choose_from_dict_with_preview(
                options_to_preview_mapping=options_to_preview_mapping,
                extension="md",
                multi=False,
                preview_size_percent=70.0,
            )
        except Exception:
            pass
    if multi:
        chosen_multi_options = choose_from_options(
            msg=msg,
            multi=True,
            options=list(options_to_preview_mapping.keys()),
            tv=True,
            custom_input=False,
        )
        if not isinstance(chosen_multi_options, list):
            return []
        return chosen_multi_options
    return choose_from_options(
        msg=msg,
        multi=False,
        options=list(options_to_preview_mapping.keys()),
        tv=True,
        custom_input=False,
    )
