import shutil

from stackops.scripts.python.helpers.helpers_utils.autostart_entry import (
    NAME_GAPS,
    StartupEntryAdded,
    StartupEntryFailure,
    StartupEntryRemoved,
    add_startup_entry,
    remove_startup_entry,
)
from stackops.utils.schemas.layouts.layout_file import read_layouts_file
from stackops.utils.schemas.startup.startup_types import StartupWhen
from stackops.utils.source_of_truth import DOTFILES_LAYOUT_YAML_PATH


# One of the layouts in the layout.yaml of the dotfiles, launched the way `terminal run --source user --choose-layouts` launches it: its
# sessions are started in the background, in the multiplexer the settings name, and are there to attach to. Sessions that are already
# running under its name are left as they are. A layout file that cannot be read raises as `read_layouts_file` does.
def add_startup_layout(layout_name: str, search_path: str, when: StartupWhen) -> StartupEntryAdded | StartupEntryFailure:
    if not DOTFILES_LAYOUT_YAML_PATH.is_file() or all(layout["layoutName"] != layout_name for layout in read_layouts_file(path=DOTFILES_LAYOUT_YAML_PATH)["layouts"]):
        return StartupEntryFailure(reason="missing_layout", message=f"""There is no layout called {layout_name} in {DOTFILES_LAYOUT_YAML_PATH}.""")
    program = shutil.which("stackops", path=search_path)
    if program is None:
        return StartupEntryFailure(reason="missing_program", message=f"""Layout {layout_name} is launched by stackops, which is not on PATH.""")
    return add_startup_entry(
        kind="layout", title=f"""Layout {layout_name}""", slug=NAME_GAPS.sub("-", layout_name).strip("-"),
        command=(program, "terminal", "run", "--source", "user", "--choose-layouts", layout_name), search_path=search_path, when=when,
    )


def remove_startup_layout(layout_name: str) -> StartupEntryRemoved | StartupEntryFailure:
    return remove_startup_entry(kind="layout", slug=NAME_GAPS.sub("-", layout_name).strip("-"))
