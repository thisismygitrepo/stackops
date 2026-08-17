import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final, Literal, cast

from stackops.utils.options_utils.options import choose_from_options


type FOLLOWUP_AGENT = Literal["codex", "copilot", "pi", "opencode"]
type FOLLOWUP_ACTION = Literal["resume", "fork"]
_UPDATE_COLUMNS: Final[tuple[str, ...]] = ("agent", "session-id", "topic", "actionsTaken", "date")
_AGENT_BY_LABEL: Final[dict[str, FOLLOWUP_AGENT]] = {
    "codex": "codex",
    "copilot": "copilot",
    "github copilot": "copilot",
    "pi": "pi",
    "opencode": "opencode",
    "omp": "opencode",
    "oh my pi": "opencode",
}
_AGENT_DISPLAY_NAME: Final[dict[FOLLOWUP_AGENT, str]] = {
    "codex": "Codex",
    "copilot": "Copilot",
    "pi": "Pi",
    "opencode": "OMP",
}
_NON_RESUMABLE_SESSION_IDS: Final[frozenset[str]] = frozenset({"not-exposed"})


@dataclass(frozen=True, slots=True)
class FollowupSession:
    agent: FOLLOWUP_AGENT
    session_id: str
    topic: str
    updated_on: date
    update_path: Path


def load_followup_sessions(*, second_brain_root: Path) -> list[FollowupSession]:
    update_paths = sorted(path for path in second_brain_root.rglob("update.csv") if path.is_file())
    if len(update_paths) == 0:
        raise ValueError(f"No update.csv files found under the Second Brain directory: {second_brain_root}")

    sessions_by_identity: dict[tuple[FOLLOWUP_AGENT, str], FollowupSession] = {}
    for update_path in update_paths:
        with update_path.open(mode="r", encoding="utf-8", newline="") as update_file:
            reader = csv.DictReader(update_file)
            if reader.fieldnames != list(_UPDATE_COLUMNS):
                expected = ",".join(_UPDATE_COLUMNS)
                actual = ",".join(reader.fieldnames or [])
                raise ValueError(f"Invalid update.csv header in {update_path}. Expected '{expected}', found '{actual}'.")

            for row in reader:
                values = [row[column] for column in _UPDATE_COLUMNS]
                if any(value is None or value.strip() == "" for value in values):
                    raise ValueError(f"Empty update.csv value in {update_path} at row {reader.line_num}.")

                agent_label, session_id, topic, _actions_taken, updated_on_text = cast(list[str], values)
                normalized_session_id = session_id.strip()
                if normalized_session_id.casefold() in _NON_RESUMABLE_SESSION_IDS:
                    continue

                normalized_agent_label = agent_label.strip().casefold()
                agent = _AGENT_BY_LABEL.get(normalized_agent_label)
                if agent is None:
                    raise ValueError(
                        f"Unsupported agent '{agent_label}' in {update_path} at row {reader.line_num}. "
                        f"Supported agents: {', '.join(_AGENT_DISPLAY_NAME.values())}."
                    )

                try:
                    updated_on = date.fromisoformat(updated_on_text.strip())
                except ValueError as error:
                    raise ValueError(
                        f"Invalid date '{updated_on_text}' in {update_path} at row {reader.line_num}. Expected an ISO date."
                    ) from error

                session = FollowupSession(
                    agent=agent,
                    session_id=normalized_session_id,
                    topic=topic.strip(),
                    updated_on=updated_on,
                    update_path=update_path,
                )
                identity = (session.agent, session.session_id)
                previous_session = sessions_by_identity.get(identity)
                if previous_session is None or session.updated_on >= previous_session.updated_on:
                    sessions_by_identity[identity] = session

    sessions = sorted(
        sessions_by_identity.values(),
        key=lambda session: (session.updated_on, session.agent, session.session_id),
        reverse=True,
    )
    if len(sessions) == 0:
        raise ValueError(f"No resumable sessions found in update.csv files under: {second_brain_root}")
    return sessions


def choose_followup_session(*, second_brain_root: Path) -> FollowupSession:
    sessions = load_followup_sessions(second_brain_root=second_brain_root)
    session_by_label = {
        (
            f"{_AGENT_DISPLAY_NAME[session.agent]} · {session.session_id} · {session.updated_on.isoformat()} · "
            f"{session.update_path.parent.relative_to(second_brain_root)} · {session.topic}"
        ): session
        for session in sessions
    }
    selected_label = choose_from_options(
        options=session_by_label,
        msg="Choose a Second Brain follow-up session",
        multi=False,
        custom_input=False,
        header="Second Brain follow-up",
        tail="",
        prompt="",
        default=None,
        tv=True,
        preview=None,
    )
    if selected_label is None:
        raise ValueError("Follow-up session selection was canceled.")
    return session_by_label[selected_label]


def build_followup_command(*, session: FollowupSession, action: FOLLOWUP_ACTION, initial_prompt: str | None) -> list[str]:
    if action == "fork" and session.agent not in ("codex", "pi"):
        raise ValueError(f"Forking follow-up sessions is not supported for {_AGENT_DISPLAY_NAME[session.agent]}.")

    match session.agent:
        case "codex":
            command = ["codex", action, "--dangerously-bypass-approvals-and-sandbox", session.session_id]
        case "copilot":
            command = ["copilot", "--yolo", f"--resume={session.session_id}"]
        case "pi":
            command = ["pi", "--fork" if action == "fork" else "--session", session.session_id]
        case "opencode":
            command = ["omp", f"--resume={session.session_id}"]

    if initial_prompt is not None:
        if session.agent == "copilot":
            command.extend(["--interactive", initial_prompt])
        else:
            command.append(initial_prompt)
    return command
