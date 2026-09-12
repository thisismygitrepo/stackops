from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.omp_plugin_state import plugin_roots
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin


def validate_resource_location(*, path: Path, context: DoctorContext) -> None:
    forbidden = (context.home_directory / "dotfiles", Path.home() / "dotfiles")
    if any(path.absolute().is_relative_to(root) for root in forbidden):
        raise ValueError("Protected resource excluded from cleanup")
    if not permitted_resource_path(path=path.parent, home_directory=context.home_directory):
        raise ValueError("Protected resource parent excluded from cleanup")


def reset_plugin_roots(*, agent: DoctorAgent, context: DoctorContext) -> tuple[tuple[DoctorOrigin, Path], ...]:
    locations: tuple[tuple[DoctorOrigin, Path], ...]
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
