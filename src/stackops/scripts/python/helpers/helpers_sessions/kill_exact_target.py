import subprocess
from typing import Literal, cast

from stackops.scripts.python.helpers.helpers_sessions.terminal_summary_json import collect_summary
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer


def kill_exact_target(*, backend: SessionMultiplexer, session: str | None, target_kind: Literal["window", "pane"], target_id: str) -> None:
    if not target_id.strip():
        raise ValueError("An exact target ID must not be blank")
    if backend == "aoe":
        raise ValueError("AoE exposes sessions only; supply NAME without --window-id or --pane-id")
    if backend == "tuios" and target_kind == "pane":
        raise ValueError("TUIOS exposes windows; use --window-id from terminal summary --json --tabs")
    records = collect_summary(backend=backend, session=session, show_tabs=True)
    if backend in {"tmux", "zellij"}:
        collection_key, identity_key = "panes", f"{target_kind}_target"
    elif backend == "tuios":
        collection_key, identity_key = "windows", "window_id"
    else:
        collection_key, identity_key = ("tabs", "tab_id") if target_kind == "window" else ("panes", "pane_id")
    matching_sessions: list[str] = []
    for record in records:
        raw_entries = record.get(collection_key)
        if not isinstance(raw_entries, list):
            raise ValueError(f"Backend summary does not contain {collection_key}")
        entries = cast(list[dict[str, object]], raw_entries)
        if any(str(entry.get(identity_key)) == target_id for entry in entries):
            session_name = record.get("name")
            if not isinstance(session_name, str):
                raise ValueError("Backend summary contains an invalid session name")
            matching_sessions.append(session_name)
    if len(matching_sessions) != 1:
        detail = "was not found" if not matching_sessions else "is ambiguous; supply NAME to select one session/workspace"
        raise ValueError(f"{target_kind.title()} ID {target_id!r} {detail}. Inspect terminal summary --json --tabs.")
    session_name = matching_sessions[0]
    match backend:
        case "tmux":
            command = ["tmux", f"kill-{target_kind}", "-t", target_id]
        case "tuios":
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import kill_window_command

            command = kill_window_command(session_name, target_id)
        case "zellij":
            command = ["zellij", "--session", session_name, "action"]
            command.extend(["close-tab-by-id", target_id] if target_kind == "window" else ["close-pane", "--pane-id", target_id])
        case "herdr":
            command = ["herdr", "tab" if target_kind == "window" else "pane", "close", target_id]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Could not close {target_kind} {target_id}: {result.stderr.strip() or result.stdout.strip()}")
