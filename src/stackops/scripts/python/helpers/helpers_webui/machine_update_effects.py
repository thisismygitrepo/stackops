from pathlib import Path
from typing import TypedDict


# The programs whose packaged settings the update can put in place of the person's own. `present` names the ones that have a settings file in its
# usual place on this machine now, which is what would be replaced.
class SettingsEffect(TypedDict):
    programs: int
    present: list[str]


# The shell's startup file, and whether it already has the line that loads StackOps.
class ShellEffect(TypedDict):
    shell: str
    profile: str
    loaded: bool


# What each of the update's optional steps would touch on this machine. A part that cannot be read is None and the page describes that step in
# general terms.
class UpdateEffects(TypedDict):
    config_folder: str
    settings: SettingsEffect | None
    shell: ShellEffect | None


# Read with the helpers the steps themselves use, so the page names what they would act on. Nothing is written.
def read_update_effects() -> UpdateEffects:
    import os
    import platform

    from stackops.profile.create_links import read_mapper
    from stackops.profile.shell_profile_source import build_shell_profile_source
    from stackops.utils.source_of_truth import CONFIG_ROOT

    settings: SettingsEffect | None = None
    try:
        mapper = read_mapper(source="library")
    except (OSError, TypeError, ValueError):
        pass
    else:
        usual_places = {program: [Path(entry["config_file_default_path"]).expanduser() for entry in entries] for program, entries in mapper.items()}
        settings = {"programs": len(mapper), "present": sorted(program for program, places in usual_places.items() if any(place.exists() or place.is_symlink() for place in places))}
    shell: ShellEffect | None = None
    try:
        source = build_shell_profile_source(system_name=platform.system(), shell_variable=os.environ.get("SHELL"), config_root=CONFIG_ROOT)
    except (OSError, ValueError):
        pass
    else:
        profile = source.profile_path
        loaded = profile.is_file() and any(line.strip() == source.source_line for line in profile.read_text(encoding="utf-8").splitlines())
        shell = {"shell": source.shell_name, "profile": str(profile), "loaded": loaded}
    return {"config_folder": str(CONFIG_ROOT), "settings": settings, "shell": shell}
