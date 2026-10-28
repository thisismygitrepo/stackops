import sys
from pathlib import Path
from typing import Literal

from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.options_utils.options import choose_from_options
from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview


def choose_edit_source(*, locations: list[tuple[str, Path]]) -> tuple[Literal["workspace", "user", "library"], Path]:
    if not sys.stdin.isatty():
        raise ValueError("--edit requires a specific --source (workspace, user, or library) when input is not interactive.")

    source_descriptions: dict[str, str] = {
        "workspace": """Workspace configuration

Use for prompts, parallel runs and MCP definitions that belong with a workspace.
These files can be committed and shared with the workspace.
""",
        "user": """Personal configuration

Use for your own prompts, parallel runs and MCP definitions, reused across workspaces.
These files are kept in your user dotfiles storage, separately from each workspace.
The source name does not set file permissions or encrypt the contents.
""",
        "library": """Built-in StackOps configuration

Use when changing the configuration bundled with the installed StackOps package.
With an editable installation, these files live in the StackOps source checkout.

Edits change the bundled files directly and may be replaced by an upgrade or reinstall.
""",
    }
    source_previews: dict[str, str] = {}
    source_locations: dict[str, tuple[Literal["workspace", "user", "library"], Path]] = {}
    for location_name, path in locations:
        source = location_name.partition(":")[0]
        match source:
            case "workspace" | "user" | "library":
                label = f"""workspace:{path.relative_to(Path.cwd(), walk_up=True).as_posix()}""" if source == "workspace" else source
                source_locations[label] = (source, path)
                source_previews[label] = f"""{label}

File to edit: {path}

{source_descriptions[source]}
"""
            case _:
                raise ValueError(f"""Unknown edit source: {location_name}""")
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
    if selected_source is None:
        raise ValueError("Source selection cancelled; no files were edited.")
    if selected_source not in source_locations:
        raise ValueError(f"""Unknown edit source: {selected_source}""")
    return source_locations[selected_source]
