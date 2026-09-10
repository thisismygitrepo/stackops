from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_constants import (
    AGENT_DISPLAY_NAME,
    FOLLOWUP_AGENT,
    NON_RESUMABLE_SESSION_IDS,
)
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_records import read_second_brain_updates
from stackops.utils.options_utils.options import choose_from_options


type FOLLOWUP_ACTION = Literal["resume", "fork"]


@dataclass(frozen=True, slots=True)
class FollowupSession:
    agent: FOLLOWUP_AGENT
    session_id: str
    topic: str
    updated_on: date
    update_path: Path


def load_followup_sessions(*, second_brain_root: Path) -> list[FollowupSession]:
    update_files = read_second_brain_updates(second_brain_root=second_brain_root)
    if len(update_files) == 0:
        raise ValueError(f"No update.csv files found under the Second Brain directory: {second_brain_root}")

    sessions_by_identity: dict[tuple[FOLLOWUP_AGENT, str], FollowupSession] = {}
    for update_file in update_files:
        if update_file.error is not None:
            typer.echo(f"""Warning: Skipping {update_file.path}: {update_file.error}""", err=True)
            continue
        for invalid_row in update_file.invalid_rows:
            typer.echo(
                f"""Warning: Skipping {update_file.path} at row {invalid_row.line_number}: {invalid_row.reason}""",
                err=True,
            )
        for record in update_file.records:
            if record.session_id.casefold() in NON_RESUMABLE_SESSION_IDS:
                continue
            session = FollowupSession(
                agent=record.agent,
                session_id=record.session_id,
                topic=record.topic,
                updated_on=record.updated_on,
                update_path=update_file.path,
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
            f"{AGENT_DISPLAY_NAME[session.agent]} · {session.session_id} · {session.updated_on.isoformat()} · "
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
    if action == "fork" and session.agent not in ("codex", "pi", "opencode", "omp"):
        raise ValueError(f"Forking follow-up sessions is not supported for {AGENT_DISPLAY_NAME[session.agent]}.")

    match session.agent:
        case "codex":
            command = ["codex", action, "--dangerously-bypass-approvals-and-sandbox", session.session_id]
        case "copilot":
            command = ["copilot", "--yolo", f"--resume={session.session_id}"]
        case "pi":
            command = ["pi", "--fork" if action == "fork" else "--session", session.session_id]
        case "opencode":
            command = ["opencode", "--session", session.session_id]
            if action == "fork":
                command.append("--fork")
        case "omp":
            command = ["omp", "--fork" if action == "fork" else "--resume", session.session_id]

    if initial_prompt is not None:
        if session.agent == "copilot":
            command.extend(["--interactive", initial_prompt])
        elif session.agent == "opencode":
            command.extend(["--prompt", initial_prompt])
        else:
            command.append(initial_prompt)
    return command
