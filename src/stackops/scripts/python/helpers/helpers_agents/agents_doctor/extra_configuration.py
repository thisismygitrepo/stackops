import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extended_constants import CODEX_SYSTEM_ROOT
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files, permitted_hook_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin, DoctorResource


def extended_configuration_resources(*, agent: DoctorAgent, context: DoctorContext) -> tuple[DoctorResource, ...]:
    paths: list[tuple[DoctorOrigin, Path, str]] = []
    if agent == "codex":
        paths.append(("admin", CODEX_SYSTEM_ROOT / "requirements.toml", "Managed Codex requirements"))
        children = hook_directory_files(directory=context.codex_home, context=context)
        if not isinstance(children, str):
            paths.extend(("global", path, "Codex named profile; loaded when selected") for path in children if path.name.endswith(".config.toml"))
    elif agent == "opencode":
        config = os.environ.get("OPENCODE_CONFIG")
        if config:
            path = Path(config).expanduser()
            paths.append(("global", path if path.is_absolute() else context.working_directory / path, "OpenCode OPENCODE_CONFIG override"))
        config_directory = os.environ.get("OPENCODE_CONFIG_DIR")
        if config_directory:
            root = Path(config_directory).expanduser()
            if not root.is_absolute():
                root = context.working_directory / root
            paths.extend(("global", root / name, "OpenCode OPENCODE_CONFIG_DIR override") for name in ("opencode.json", "opencode.jsonc"))
    return tuple(
        DoctorResource("configuration", True, path.name, origin, "configured", path, detail)
        for origin, path, detail in paths
        if permitted_hook_path(path=path, context=context) and path.is_file()
    )
