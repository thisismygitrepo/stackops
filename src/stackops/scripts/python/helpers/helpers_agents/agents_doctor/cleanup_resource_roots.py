from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugin_state import plugin_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants import CODEX_SYSTEM_PLUGIN_SOURCES
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin


def validate_resource_location(*, path: Path, context: DoctorContext) -> None:
    forbidden = (context.home_directory / "dotfiles", Path.home() / "dotfiles")
    if any(path.absolute().is_relative_to(root) for root in forbidden):
        raise ValueError("Protected resource excluded from cleanup")
    if not permitted_resource_path(path=path.parent, home_directory=context.home_directory):
        raise ValueError("Protected resource parent excluded from cleanup")


def plugin_removal_targets(*, agent: DoctorAgent, root: Path, context: DoctorContext) -> tuple[Path, ...]:
    validate_resource_location(path=root, context=context)
    if root.is_symlink():
        return (root,)
    if not root.exists():
        return ()
    if agent != "codex" or root != context.codex_home / "plugins":
        return (root,)
    cache = root / "cache"
    if cache.is_symlink():
        return (root,)
    try:
        sources = sorted(cache.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return (root,)
    if not any(source.name in CODEX_SYSTEM_PLUGIN_SOURCES for source in sources):
        return (root,)
    return (
        *(child for child in sorted(root.iterdir()) if child.name.casefold() != cache.name),
        *(source for source in sources if source.name not in CODEX_SYSTEM_PLUGIN_SOURCES),
    )


def reset_plugin_roots(*, agent: DoctorAgent, context: DoctorContext) -> tuple[tuple[DoctorOrigin, Path], ...]:
    locations: tuple[tuple[DoctorOrigin, Path], ...]
    names: tuple[str, ...]
    match agent:
        case "claude":
            locations = (("global", context.claude_home), *(("local", path / ".claude") for path in context.ancestor_directories))
            names = ("plugins",)
        case "codex":
            locations = (("global", context.codex_home), *(("local", path / ".codex") for path in context.ancestor_directories))
            names = ("plugins",)
        case "pi":
            locations = (("global", context.pi_home), ("local", context.working_directory / ".pi"))
            names = ("extensions",)
        case "omp":
            return (
                *((origin, path) for origin, path, _detail in plugin_roots(context=context)),
                ("global", context.omp_home / "extensions"),
                *(("local", path / ".omp" / "extensions") for path in context.ancestor_directories),
            )
        case "opencode":
            locations = (("global", context.xdg_config_directory / "opencode"), *(("local", path / ".opencode") for path in context.ancestor_directories))
            names = ("plugins", "plugin")
        case "qwen":
            locations = (("global", context.home_directory / ".qwen"), ("local", context.project_root / ".qwen"))
            names = ("extensions",)
        case "droid":
            locations = (("global", context.home_directory / ".factory"), ("local", context.project_root / ".factory"))
            names = ("plugins",)
        case "cline":
            locations = (("global", context.home_directory / ".cline"), ("local", context.project_root / ".cline"))
            names = ("plugins",)
        case "agy":
            locations = (("global", context.home_directory / ".gemini"),)
            names = ("extensions",)
        case _:
            return ()
    return tuple((origin, root / name) for origin, root in locations for name in names)
