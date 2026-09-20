import os
from pathlib import Path
from typing import Final

from stackops.utils.sandbox.options import SandboxAccess

_PROVIDER_ENVIRONMENT: Final[tuple[str, ...]] = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_OAUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "COPILOT_GITHUB_TOKEN",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_CLOUD_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_BASE_URL",
    "AZURE_OPENAI_API_VERSION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_BEARER_TOKEN_BEDROCK",
    "OPENROUTER_API_KEY",
    "AI_GATEWAY_API_KEY",
    "XAI_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "ZAI_API_KEY",
    "OPENCODE_API_KEY",
    "HF_TOKEN",
    "KIMI_API_KEY",
    "MINIMAX_API_KEY",
    "MINIMAX_CN_API_KEY",
    "DEEPSEEK_API_KEY",
)
_XDG_DIRECTORIES: Final[tuple[tuple[str, str], ...]] = (
    ("XDG_CONFIG_HOME", ".config"),
    ("XDG_DATA_HOME", ".local/share"),
    ("XDG_STATE_HOME", ".local/state"),
    ("XDG_CACHE_HOME", ".cache"),
)


def _environment_directory(*, name: str, default_directory: Path) -> Path:
    configured_directory = os.environ.get(name)
    if configured_directory is None or configured_directory.strip() == "":
        return default_directory.absolute()
    return Path(configured_directory).expanduser().absolute()


def resolve_sandbox_access(*, agent: str) -> SandboxAccess:
    home_directory = Path.home()
    directories: tuple[Path, ...]
    environment: tuple[str, ...]
    match agent:
        case "codex":
            directories = (_environment_directory(name="CODEX_HOME", default_directory=home_directory / ".codex"),)
            environment = ("CODEX_HOME", "OPENAI_API_KEY", "OPENAI_BASE_URL")
        case "copilot":
            directories = (_environment_directory(name="COPILOT_HOME", default_directory=home_directory / ".copilot"),)
            environment = (
                "COPILOT_HOME",
                "COPILOT_GITHUB_TOKEN",
                "GH_TOKEN",
                "GITHUB_TOKEN",
                "COPILOT_GH_HOST",
                "GH_HOST",
                "COPILOT_PROVIDER_BASE_URL",
                "COPILOT_PROVIDER_API_KEY",
                "COPILOT_MODEL",
            )
        case "deepseek":
            directories = (
                _environment_directory(name="DSH_HOME", default_directory=home_directory / ".dsh"),
                _environment_directory(name="DSH_AGENTS_HOME", default_directory=home_directory / ".agents"),
            )
            environment = ("DSH_HOME", "DSH_AGENTS_HOME", "DSH_PERMISSION_MODE", *_PROVIDER_ENVIRONMENT)
            return SandboxAccess(
                writable_paths=directories, environment_names=environment,
                environment_overrides={"DSH_TELEMETRY_DISABLED": "1", "DSH_TELEMETRY_MODE": "DISABLED"},
            )
        case "pi":
            directories = (_environment_directory(name="PI_CODING_AGENT_DIR", default_directory=home_directory / ".pi/agent"),)
            environment = ("PI_CODING_AGENT_DIR", *_PROVIDER_ENVIRONMENT)
        case "omp":
            profile = os.environ.get("OMP_PROFILE")
            if profile is not None and profile.strip() not in ("", "default"):
                directory = home_directory.joinpath(".omp", "profiles", profile.strip(), "agent").absolute()
            else:
                directory = _environment_directory(name="PI_CODING_AGENT_DIR", default_directory=home_directory / ".omp/agent")
            plugin_directory = directory.parent / "plugins"
            configured_data_directory = os.environ.get("XDG_DATA_HOME")
            if configured_data_directory is not None and configured_data_directory.strip() != "":
                data_directory = Path(configured_data_directory).expanduser().absolute() / "omp"
                if profile is not None and profile.strip() not in ("", "default"):
                    data_directory = data_directory / "profiles" / profile.strip()
                plugin_directory = data_directory / "plugins"
            directories = (directory, plugin_directory)
            environment = ("OMP_PROFILE", "PI_CODING_AGENT_DIR", "XDG_DATA_HOME", *_PROVIDER_ENVIRONMENT)
        case "opencode":
            directories = tuple(
                _environment_directory(name=name, default_directory=home_directory / suffix) / "opencode"
                for name, suffix in _XDG_DIRECTORIES
            )
            environment = (*(name for name, _suffix in _XDG_DIRECTORIES), *_PROVIDER_ENVIRONMENT)
        case _:
            from stackops.scripts.python.helpers.helpers_agents.agents_sandbox_prompt_access import resolve_prompt_sandbox_access

            return resolve_prompt_sandbox_access(agent=agent, provider_environment=_PROVIDER_ENVIRONMENT, xdg_directories=_XDG_DIRECTORIES)
    return SandboxAccess(writable_paths=directories, environment_names=environment, environment_overrides={})
