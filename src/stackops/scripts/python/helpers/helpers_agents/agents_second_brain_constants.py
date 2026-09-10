from typing import Final, Literal


type FOLLOWUP_AGENT = Literal["codex", "copilot", "pi", "opencode", "omp"]
UPDATE_COLUMNS: Final[tuple[str, ...]] = ("agent", "session-id", "topic", "actionsTaken", "date")
AGENT_BY_LABEL: Final[dict[str, FOLLOWUP_AGENT]] = {
    "codex": "codex",
    "copilot": "copilot",
    "github copilot": "copilot",
    "pi": "pi",
    "opencode": "opencode",
    "omp": "omp",
    "oh my pi": "omp",
}
AGENT_DISPLAY_NAME: Final[dict[FOLLOWUP_AGENT, str]] = {
    "codex": "Codex",
    "copilot": "Copilot",
    "pi": "Pi",
    "opencode": "OpenCode",
    "omp": "Oh My Pi",
}
NON_RESUMABLE_SESSION_IDS: Final[frozenset[str]] = frozenset({"not-exposed"})
