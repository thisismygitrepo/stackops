import platform
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
# On Linux the launch is put in a scope of its own. systemd ends whatever a unit leaves behind when the unit's command is over, and again
# when the unit is turned off, so without that the sessions would end with the launch, or with the entry being removed.
def add_startup_layout(layout_name: str, search_path: str, when: StartupWhen) -> StartupEntryAdded | StartupEntryFailure:
    if not DOTFILES_LAYOUT_YAML_PATH.is_file() or all(layout["layoutName"] != layout_name for layout in read_layouts_file(path=DOTFILES_LAYOUT_YAML_PATH)["layouts"]):
        return StartupEntryFailure(reason="missing_layout", message=f"""There is no layout called {layout_name} in {DOTFILES_LAYOUT_YAML_PATH}.""")
    stackops = shutil.which("stackops", path=search_path)
    if stackops is None:
        return StartupEntryFailure(reason="missing_program", message=f"""Layout {layout_name} is launched by stackops, which is not on PATH.""")
    command: tuple[str, ...] = (stackops, "terminal", "run", "--source", "user", "--choose-layouts", layout_name)
    if platform.system() == "Linux":
        systemd_run = shutil.which("systemd-run", path=search_path)
        if systemd_run is None:
            return StartupEntryFailure(reason="missing_program", message=f"""Layout {layout_name} is launched through systemd-run, which is not on PATH.""")
        command = (systemd_run, "--user", "--scope", "--quiet", "--", *command)
    return add_startup_entry(kind="layout", title=f"""Layout {layout_name}""", slug=NAME_GAPS.sub("-", layout_name).strip("-"), command=command, search_path=search_path, when=when)


def remove_startup_layout(layout_name: str) -> StartupEntryRemoved | StartupEntryFailure:
    return remove_startup_entry(kind="layout", slug=NAME_GAPS.sub("-", layout_name).strip("-"))
