from typing import Final, Literal, TypeAlias, TypedDict, cast, get_args


AGENTS: TypeAlias = Literal[
    "agy",
    "cursor-agent",
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
    "oz",
    "droid",
    "pi",
]
CONFIG_AGENTS: TypeAlias = AGENTS | Literal["omp"]
CONFIG_AGENT_VALUES: Final[tuple[CONFIG_AGENTS, ...]] = (
    *cast(tuple[AGENTS, ...], get_args(AGENTS)),
    "omp",
)
DEFAULT_AGENT: Final[AGENTS] = "codex"
HOST: TypeAlias = Literal["local", "docker"]
PROVIDER: TypeAlias = Literal[
    "azure",
    "azure-openai-responses",
    "google",
    "aws",
    "amazon-bedrock",
    "openai",
    "anthropic",
    "openrouter",
    "xai",
    "mistral",
    "groq",
    "cerebras",
    "vercel-ai-gateway",
    "zai",
    "opencode",
    "opencode-go",
    "huggingface",
    "kimi-coding",
    "minimax",
    "minimax-cn",
]
ReasoningEffort: TypeAlias = Literal["none", "low", "medium", "high", "xhigh"]
DEFAULT_SEAPRATOR = "\n@-@\n"
DEFAULT_STAGGER_MAX = 3.0


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


SEARCH_STRATEGIES: TypeAlias = Literal["file_path", "keyword_search", "filename_pattern"]
