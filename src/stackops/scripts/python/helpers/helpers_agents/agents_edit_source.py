import sys
from typing import Literal

from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.options_utils.options import choose_from_options
from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_STACKOPS_ROOT, LIBRARY_ROOT


def choose_edit_source() -> Literal["repo", "private", "public", "library"]:
    if not sys.stdin.isatty():
        raise ValueError("--edit requires a specific --source (repo, private, public, or library) when input is not interactive.")

    source_previews: dict[str, str] = {
        "repo": """repo — Project configuration

Location: <project>/.stackops/

Use for prompts, parallel runs and MCP definitions that belong with a project.
These files can be committed and shared with the project.

Prompt discovery can also include project files in immediate child directories.
""",
        "private": f"""private — Personal configuration

Location: {DOTFILES_STACKOPS_ROOT}

Use for your own prompts, parallel runs and MCP definitions, reused across projects.
These files are kept in your private dotfiles storage, separately from each project.
The source name does not set file permissions or encrypt the contents.
""",
        "public": f"""public — Reusable local configuration

Location: {CONFIG_ROOT}

Use for prompts, parallel runs and MCP definitions in your local StackOps configuration,
available across projects on this machine.

Selecting public edits local files; it does not publish or upload them.
""",
        "library": f"""library — Built-in StackOps configuration

Location: {LIBRARY_ROOT}

Use when changing the configuration bundled with the installed StackOps package.
With an editable installation, these files live in the StackOps source checkout.

Edits change the bundled files directly and may be replaced by an upgrade or reinstall.
""",
    }
    if check_tool_exists("tv"):
        selected_source = choose_from_dict_with_preview(
            options_to_preview_mapping=source_previews,
            extension="txt",
            multi=False,
            preview_size_percent=70,
        )
    else:
        selected_source = choose_from_options(
            options=tuple(source_previews),
            msg="Select a source to edit\n\n" + "\n".join(source_previews.values()),
            multi=False,
            custom_input=False,
            header="Edit source",
            tail="",
            prompt="",
            default=None,
            tv=False,
            preview=None,
        )
    match selected_source:
        case "repo" | "private" | "public" | "library":
            return selected_source
        case None:
            raise ValueError("Source selection cancelled; no files were edited.")
        case _:
            raise ValueError(f"""Unknown edit source: {selected_source}""")
