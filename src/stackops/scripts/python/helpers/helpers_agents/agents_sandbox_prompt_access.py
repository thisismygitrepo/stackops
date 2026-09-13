import os
import platform
from pathlib import Path

from stackops.utils.sandbox.options import SandboxAccess


def _configured_directory(*, name: str, directory: Path) -> Path:
    configured = os.environ.get(name)
    if configured is None or not configured.strip():
        return directory.absolute()
    return Path(configured).expanduser().absolute()


def resolve_prompt_sandbox_access(
    *, agent: str, provider_environment: tuple[str, ...], xdg_directories: tuple[tuple[str, str], ...],
) -> SandboxAccess:
    home = Path.home()
    host_system = platform.system()
    xdg = {name: _configured_directory(name=name, directory=home / suffix) for name, suffix in xdg_directories}
    xdg_environment = tuple(xdg)
    local_app_data = _configured_directory(name="LOCALAPPDATA", directory=home / "AppData/Local")
    roaming_app_data = _configured_directory(name="APPDATA", directory=home / "AppData/Roaming")
    environment_overrides: dict[str, str] = {}
    directories: tuple[Path, ...]
    environment: tuple[str, ...]
    match agent:
        case "agy":
            directories = (home / ".gemini/antigravity-cli",)
            environment = ("GEMINI_API_KEY", "GOOGLE_GEMINI_BASE_URL", "AGY_CLI_DISABLE_AUTO_UPDATE")
        case "cursor-agent":
            directory = home / ".cursor"
            if host_system == "Linux" and os.environ.get("XDG_CONFIG_HOME", "").strip():
                directory = xdg["XDG_CONFIG_HOME"] / "cursor"
            directories = (_configured_directory(name="CURSOR_CONFIG_DIR", directory=directory),)
            environment_overrides = {"CURSOR_CONFIG_DIR": str(directories[0])}
            environment = ("CURSOR_CONFIG_DIR", "XDG_CONFIG_HOME", "CURSOR_API_KEY")
        case "claude":
            directories = (_configured_directory(name="CLAUDE_CONFIG_DIR", directory=home / ".claude"),)
            environment_overrides = {"CLAUDE_CONFIG_DIR": str(directories[0])}
            environment = (
                "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
                "CLAUDE_CODE_USE_FOUNDRY", "ANTHROPIC_MODEL", "ANTHROPIC_VERTEX_PROJECT_ID", "CLOUD_ML_REGION",
                *provider_environment,
            )
        case "qwen":
            directory = _configured_directory(name="QWEN_HOME", directory=home / ".qwen")
            directories = (directory, _configured_directory(name="QWEN_RUNTIME_DIR", directory=directory))
            environment = ("QWEN_HOME", "QWEN_RUNTIME_DIR", "OPENAI_MODEL", "QWEN_MODEL", *provider_environment)
        case "forge":
            directory = home / "forge" if (home / "forge").is_dir() else home / ".forge"
            directories = (_configured_directory(name="FORGE_CONFIG", directory=directory),)
            environment = ("FORGE_CONFIG", "FORGE_API_KEY", "OPENAI_URL", *provider_environment)
        case "crush":
            data_directory = xdg["XDG_DATA_HOME"] / "crush"
            cache_directory = xdg["XDG_CACHE_HOME"] / "crush"
            if host_system == "Windows":
                if not os.environ.get("XDG_DATA_HOME", "").strip():
                    data_directory = local_app_data / "crush"
                if not os.environ.get("XDG_CACHE_HOME", "").strip():
                    cache_directory = local_app_data / "crush/cache"
            config_directory = _configured_directory(name="CRUSH_GLOBAL_CONFIG", directory=xdg["XDG_CONFIG_HOME"] / "crush")
            directories = (
                config_directory, _configured_directory(name="CRUSH_GLOBAL_DATA", directory=data_directory),
                _configured_directory(name="CRUSH_CACHE_DIR", directory=cache_directory),
                _configured_directory(name="CRUSH_SKILLS_DIR", directory=config_directory / "skills"),
            )
            environment_overrides = dict(zip(
                ("CRUSH_GLOBAL_CONFIG", "CRUSH_GLOBAL_DATA", "CRUSH_CACHE_DIR", "CRUSH_SKILLS_DIR"),
                (str(directory) for directory in directories), strict=True,
            ))
            environment = (
                "CRUSH_GLOBAL_CONFIG", "CRUSH_GLOBAL_DATA", "CRUSH_CACHE_DIR", "CRUSH_SKILLS_DIR", "LOCALAPPDATA",
                "HYPER_API_KEY", "VERCEL_API_KEY", *xdg_environment, *provider_environment,
            )
        case "q":
            data_directory = home / "Library/Application Support/amazon-q" if host_system == "Darwin" else xdg["XDG_DATA_HOME"] / "amazon-q"
            directories = (xdg["XDG_CONFIG_HOME"] / "amazon-q", data_directory, home / ".amazonq", home / ".aws/amazonq")
            if host_system == "Darwin":
                environment_overrides = {"XDG_DATA_HOME": str(data_directory.parent)}
            environment = (*xdg_environment, "AWS_PROFILE", *provider_environment)
        case "kilocode":
            directories = tuple(root / "kilo" for root in xdg.values()) + (xdg["XDG_CONFIG_HOME"] / "kilocode",)
            custom_directory = os.environ.get("KILO_CONFIG_DIR")
            if custom_directory is not None and custom_directory.strip():
                directories += (Path(custom_directory).expanduser().absolute(),)
            environment = ("KILO_CONFIG_DIR", "KILO_CONFIG_CONTENT", "KILOCODE_TOKEN", *xdg_environment, *provider_environment)
        case "cline":
            directory = home / ".cline"
            directories = (
                directory, _configured_directory(name="CLINE_DATA_DIR", directory=directory / "data"),
                _configured_directory(name="CLINE_HOOKS_DIR", directory=directory / "hooks"),
            )
            environment = ("CLINE_DATA_DIR", "CLINE_HOOKS_DIR", "CLINE_API_KEY", "CLINE_COMMAND_PERMISSIONS", *provider_environment)
        case "auggie":
            directories = (home / ".augment",)
            environment = ("AUGMENT_SESSION_AUTH",)
        case "oz":
            if host_system == "Darwin":
                platform_directories = (home / "Library/Group Containers/2BBY89MBSN.dev.warp/Library/Application Support/dev.warp.Warp-Stable",)
            elif host_system == "Windows":
                platform_directories = (local_app_data / "warp/Warp", roaming_app_data / "warp/Warp")
            else:
                platform_directories = tuple(root / "warp-terminal" for root in xdg.values())
            config_directory = roaming_app_data if host_system == "Windows" else xdg["XDG_CONFIG_HOME"]
            directories = (home / ".warp", config_directory / "stackops/agents/oz", *platform_directories)
            environment = ("WARP_API_KEY", "LOCALAPPDATA", "APPDATA", *xdg_environment)
        case "droid":
            directories = (home / ".factory",)
            environment = ("FACTORY_API_KEY", "FACTORY_DROID_AUTO_UPDATE_ENABLED", *provider_environment)
        case _:
            raise ValueError(f"""Sandboxing is not supported for agent: {agent}.""")
    return SandboxAccess(
        writable_paths=tuple(dict.fromkeys(directories)),
        environment_names=tuple(dict.fromkeys(environment)),
        environment_overrides=environment_overrides,
    )
