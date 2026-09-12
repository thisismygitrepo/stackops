import os
import sys
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookSource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import hook_directory_files
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext, DoctorOrigin


def json_hook_sources(*, agent: DoctorAgent, context: DoctorContext) -> tuple[tuple[HookSource, ...], tuple[HookDiagnostic, ...]]:
    sources: list[HookSource] = []
    directories: list[tuple[DoctorOrigin, Path]] = []
    diagnostics: list[HookDiagnostic] = []
    settings_roots: list[tuple[DoctorOrigin, Path, tuple[str, ...]]] = []
    match agent:
        case "claude":
            settings_roots.append(("global", context.claude_home, ("settings.json",)))
            settings_roots.extend(("local", root / ".claude", ("settings.json", "settings.local.json")) for root in context.ancestor_directories)
            managed = Path("/Library/Application Support/ClaudeCode") if sys.platform == "darwin" else Path("/etc/claude-code")
            sources.append(HookSource(agent, "admin", managed / "managed-settings.json", ("hooks",)))
            directories.append(("admin", managed / "managed-settings.d"))
        case "qwen":
            settings_roots.append(("global", context.home_directory / ".qwen", ("settings.json",)))
            settings_roots.extend(("local", root / ".qwen", ("settings.json",)) for root in context.ancestor_directories)
            managed = Path("/Library/Application Support/QwenCode") if sys.platform == "darwin" else Path("/etc/qwen-code")
            sources.extend(
                (
                    HookSource(agent, "admin", Path(os.environ.get("QWEN_CODE_SYSTEM_SETTINGS_PATH", str(managed / "settings.json"))), ("hooks",)),
                    HookSource(
                        agent, "system", Path(os.environ.get("QWEN_CODE_SYSTEM_DEFAULTS_PATH", str(managed / "system-defaults.json"))), ("hooks",)
                    ),
                )
            )
        case "droid":
            settings_roots.append(("global", context.home_directory / ".factory", ("settings.json",)))
            settings_roots.extend(("local", root / ".factory", ("settings.json",)) for root in context.ancestor_directories)
            managed = Path("/Library/Application Support/Factory") if sys.platform == "darwin" else Path("/etc/factory")
            sources.append(HookSource(agent, "admin", managed / "settings.json", ("hooks",)))
        case "cursor-agent":
            configured = os.environ.get("CURSOR_CONFIG_DIR")
            cursor_home = Path(configured).expanduser() if configured else context.home_directory / ".cursor"
            sources.extend(
                (
                    HookSource(agent, "global", cursor_home / "hooks.json", ("hooks",)),
                    HookSource(agent, "local", context.project_root / ".cursor/hooks.json", ("hooks",)),
                )
            )
            managed = Path("/Library/Application Support/Cursor") if sys.platform == "darwin" else Path("/etc/cursor")
            sources.append(HookSource(agent, "admin", managed / "hooks.json", ("hooks",)))
        case "copilot":
            copilot_home = Path(os.environ.get("COPILOT_HOME", str(context.home_directory / ".copilot"))).expanduser()
            settings_roots.extend(
                (
                    ("global", copilot_home, ("settings.json",)),
                    ("local", context.project_root / ".github/copilot", ("settings.json", "settings.local.json")),
                    ("local", context.project_root / ".claude", ("settings.json", "settings.local.json")),
                )
            )
            directories.extend(
                (
                    ("global", copilot_home / "hooks"),
                    ("local", context.project_root / ".github/hooks"),
                    ("admin", Path("/etc/github-copilot/policy.d")),
                )
            )
        case "q":
            directories.append(("global", context.home_directory / ".aws/amazonq/cli-agents"))
            directories.extend(("local", root / ".amazonq/cli-agents") for root in context.ancestor_directories)
        case _:
            pass
    for origin, directory, names in settings_roots:
        for name in names:
            sources.append(HookSource(agent, origin, directory / name, ("hooks",)))
        if agent == "droid":
            sources.extend((HookSource(agent, origin, directory / "hooks.json", ()), HookSource(agent, origin, directory / "hooks/hooks.json", ())))
    for origin, directory in directories:
        paths = hook_directory_files(directory=directory, context=context)
        if isinstance(paths, str):
            diagnostics.append(HookDiagnostic(agent, origin, directory, paths, "error"))
            continue
        sources.extend(HookSource(agent, origin, path, ("hooks",)) for path in paths if path.suffix == ".json")
    return tuple(dict.fromkeys(sources)), tuple(diagnostics)
