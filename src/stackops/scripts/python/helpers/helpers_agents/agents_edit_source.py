import sys
from typing import Literal

from stackops.utils.options_utils.options import choose_from_options


def choose_edit_source() -> Literal["repo", "private", "public", "library"]:
    if not sys.stdin.isatty():
        raise ValueError("--edit requires a specific --source (repo, private, public, or library) when input is not interactive.")

    sources: tuple[Literal["repo", "private", "public", "library"], ...] = ("repo", "private", "public", "library")
    selected_source = choose_from_options(
        options=sources,
        msg="Select a source to edit",
        multi=False,
        custom_input=False,
        header="Edit source",
        tail="",
        prompt="",
        default=None,
        tv=True,
        preview=None,
    )
    if selected_source is None:
        raise ValueError("Source selection cancelled; no files were edited.")
    return selected_source
