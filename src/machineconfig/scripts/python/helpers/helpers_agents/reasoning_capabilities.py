from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, ReasoningEffort


ReasoningShortcut: TypeAlias = Literal["n", "l", "m", "h", "x"]


@dataclass(frozen=True, slots=True)
class AgentReasoningSupport:
    efforts: tuple[ReasoningEffort, ...]
    note: str | None


_EFFORT_BY_SHORTCUT: Final[dict[ReasoningShortcut, ReasoningEffort]] = {
    "n": "none",
    "l": "low",
    "m": "medium",
    "h": "high",
    "x": "xhigh",
}

_SHORTCUT_BY_EFFORT: Final[dict[ReasoningEffort, ReasoningShortcut]] = {
    effort: shortcut for shortcut, effort in _EFFORT_BY_SHORTCUT.items()
}

_AGENT_REASONING_SUPPORT: Final[dict[AGENTS, AgentReasoningSupport]] = {
    "cursor-agent": AgentReasoningSupport(efforts=(), note=None),
    "gemini": AgentReasoningSupport(efforts=(), note=None),
    "claude": AgentReasoningSupport(
        efforts=("low", "medium", "high"),
        note="actual support depends on the selected Claude model",
    ),
    "qwen": AgentReasoningSupport(efforts=(), note=None),
    "copilot": AgentReasoningSupport(efforts=("low", "medium", "high", "xhigh"), note=None),
    "codex": AgentReasoningSupport(
        efforts=("none", "low", "medium", "high", "xhigh"),
        note="actual model support can be a narrower subset",
    ),
    "crush": AgentReasoningSupport(efforts=(), note=None),
    "q": AgentReasoningSupport(efforts=(), note=None),
    "opencode": AgentReasoningSupport(efforts=(), note=None),
    "kilocode": AgentReasoningSupport(efforts=(), note=None),
    "cline": AgentReasoningSupport(efforts=(), note=None),
    "auggie": AgentReasoningSupport(efforts=(), note=None),
    "warp-cli": AgentReasoningSupport(efforts=(), note=None),
    "droid": AgentReasoningSupport(efforts=(), note=None),
}


def _format_shortcut(effort: ReasoningEffort) -> str:
    return f"""{_SHORTCUT_BY_EFFORT[effort]}={effort}"""


def reasoning_help(agent: AGENTS) -> str:
    support = _AGENT_REASONING_SUPPORT[agent]
    shortcuts = ", ".join(_format_shortcut(effort=effort) for effort in support.efforts)
    if support.note is None:
        return shortcuts
    return f"""{shortcuts}; {support.note}"""


def reasoning_support(agent: AGENTS) -> AgentReasoningSupport:
    return _AGENT_REASONING_SUPPORT[agent]


def resolve_reasoning(shortcut: ReasoningShortcut, agent: AGENTS) -> ReasoningEffort:
    effort = _EFFORT_BY_SHORTCUT[shortcut]
    support = reasoning_support(agent=agent)
    if effort in support.efforts:
        return effort
    supported = ", ".join(_format_shortcut(effort=supported_effort) for supported_effort in support.efforts)
    raise ValueError(f"""agent {agent!r} does not support {shortcut!r}; supported values: {supported}""")
