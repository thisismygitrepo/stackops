from typing import Literal, TypeAlias, TypedDict


# Vscode extensions for AI-assisted coding.
# Github copilot
# Roo
# Cline
# Kilocode
# Continue
# CodeGPT
# qodo (and cli)

# Editors based on AI
# Kiro
# Cursor
# Warp

AGENTS: TypeAlias = Literal[
    "cursor-agent",
    "gemini",
    "claude",
    "qwen",
    "copilot",
    "codex",
    "forge",
    "crush",
    "q",
    "opencode",
    "kilocode",
    "cline",
    "auggie",
    "warp-cli",
    "droid",
]
HOST: TypeAlias = Literal["local", "docker"]
PROVIDER: TypeAlias = Literal[
    "azure", "google", "aws", "openai", "anthropic", "openrouter", "xai"
]
ReasoningEffort: TypeAlias = Literal["none", "low", "medium", "high", "xhigh"]
DEFAULT_SEAPRATOR = "\n@-@\n"


class API_SPEC(TypedDict):
    api_key: str | None
    api_name: str
    api_label: str
    api_account: str


class AI_SPEC(TypedDict):
    provider: PROVIDER | None
    model: str | None
    agent: AGENTS
    machine: HOST
    api_spec: API_SPEC
    reasoning_effort: ReasoningEffort | None


AGENT_NAME_FORMATTER = "agent_{idx}_cmd.sh"  # e.g., agent_0_cmd.sh
SEARCH_STRATEGIES: TypeAlias = Literal[
    "file_path", "keyword_search", "filename_pattern"
]
