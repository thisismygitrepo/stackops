from typing import Final

from stackops.utils.schemas.fire_agents.fire_agents_types import CONFIG_AGENTS


OPENROUTER_ZDR_CONFIGURATION: Final[dict[CONFIG_AGENTS, str | None]] = {
    "agy": None,
    "cursor-agent": None,
    "claude": "ZDR added when project settings select OpenRouter",
    "qwen": "ZDR added to existing repository OpenRouter model settings",
    "copilot": "Requires OpenRouter account/API-key enforcement",
    "codex": "Requires OpenRouter account/API-key enforcement",
    "deepseek": "Requires OpenRouter account/API-key enforcement",
    "forge": "Requires OpenRouter account/API-key enforcement",
    "crush": "OpenRouter provider request defaults",
    "q": None,
    "opencode": "OpenRouter provider request defaults",
    "kilocode": "OpenRouter provider request defaults",
    "cline": "Requires OpenRouter account/API-key enforcement",
    "auggie": None,
    "oz": "Requires OpenRouter account/API-key enforcement",
    "droid": "ZDR added to existing repository OpenRouter model settings",
    "pi": "OpenRouter provider request policy extension",
    "omp": "OpenRouter session request policy extension",
}
