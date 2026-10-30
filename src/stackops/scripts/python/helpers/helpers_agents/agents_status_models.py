from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias


type JsonObject = dict[str, object]
StatusBackend: TypeAlias = Literal["tuios", "herdr", "aoe"]
StatusFormat: TypeAlias = Literal["table", "json", "markdown"]
HistoryMode: TypeAlias = Literal["auto", "transcripts", "hooks", "none"]
AgentStatus: TypeAlias = Literal["working", "waiting", "blocked", "idle", "completed", "failed", "unknown", "unavailable"]


@dataclass(frozen=True)
class StatusOptions:
    backend: StatusBackend
    sessions: tuple[str, ...]
    layouts: tuple[str, ...]
    tabs: tuple[str, ...]
    windows: tuple[str, ...]
    exclude_windows: tuple[str, ...]
    agent_sessions: tuple[str, ...]
    harnesses: tuple[str, ...]
    states: tuple[str, ...]
    include_self: bool
    history: HistoryMode
    capture_lines: int
    message_limit: int
    text_limit: int
    event_limit: int
    timeout: float
    workers: int
    server: str | None
    claude_home: Path
    codex_home: Path


@dataclass(frozen=True)
class MessageRecord:
    timestamp: str
    text: str
    source: str
    kind: str
    line: int | None


@dataclass(frozen=True)
class HistoryEvidence:
    messages: tuple[MessageRecord, ...]
    latest_reply: str
    latest_reply_at: str
    sources: tuple[str, ...]
    coverage: str
    limitations: tuple[str, ...]
    omitted_messages: int


@dataclass(frozen=True)
class ProcessEvidence:
    pid: int | None
    live: bool | None
    harness: str
    cwd: str
    command: str
    session_id: str
    transcript_paths: tuple[Path, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class AgentSnapshot:
    session: str
    session_id: str
    workspace: int | None
    workspace_name: str
    workspace_id: str
    tab_id: str
    tab_name: str
    window_id: str
    window_name: str
    agent_session_name: str
    harness: str
    cwd: str
    process: ProcessEvidence
    status: AgentStatus
    task_status: str
    reported_state: str
    task: str
    latest_activity: str
    history: HistoryEvidence
    prompt: JsonObject
    capture: str
    events: tuple[JsonObject, ...]
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class StatusSnapshot:
    backend: StatusBackend
    started_at: str
    observed_at: str
    server: str | None
    agents: tuple[AgentSnapshot, ...]
    coverage: JsonObject
    limitations: tuple[str, ...]
