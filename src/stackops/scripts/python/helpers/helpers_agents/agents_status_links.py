from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import UUID


def readable_status_path(*, path: Path) -> Path:
    blocked = Path.home() / "dotfiles"
    expanded = path.expanduser()
    if expanded.is_relative_to(blocked):
        raise ValueError("Inspection of ~/dotfiles is prohibited")
    resolved = expanded.resolve()
    if resolved.is_relative_to(blocked):
        raise ValueError("Inspection of ~/dotfiles is prohibited")
    return resolved


def conversation_id(*, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Conversation metadata has no session identifier")
    try:
        return str(UUID(value))
    except ValueError as error:
        raise ValueError("Conversation metadata has an invalid session identifier") from error


def codex_transcript_metadata(*, path: Path) -> dict[str, object]:
    with readable_status_path(path=path).open(encoding="utf-8") as stream:
        first_line = stream.readline()
    row: object = json.loads(first_line)
    if not isinstance(row, dict) or row.get("type") != "session_meta":
        raise ValueError("Codex transcript has no leading session metadata")
    payload = row.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Codex transcript session metadata is invalid")
    return payload


def claude_session_id(
    *, home: Path, pid: int, cwd: str, created_at: float, registered_id: str
) -> tuple[str, tuple[str, ...]]:
    metadata_path = readable_status_path(path=home / "sessions" / f"""{pid}.json""")
    if not metadata_path.is_file():
        if registered_id:
            return conversation_id(value=registered_id), ("Claude PID metadata is unavailable; using the registered conversation ID.",)
        raise ValueError("Claude PID metadata is unavailable; no conversation can be linked")
    metadata: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or metadata.get("pid") != pid:
        raise ValueError("Claude PID metadata does not match the live process")
    recorded_cwd = metadata.get("cwd")
    if isinstance(recorded_cwd, str) and cwd:
        if readable_status_path(path=Path(recorded_cwd)) != readable_status_path(path=Path(cwd)):
            raise ValueError("Claude PID metadata working directory conflicts with the live process")
    recorded_start = metadata.get("procStart")
    if isinstance(recorded_start, str) and recorded_start:
        starts = {
            datetime.fromtimestamp(created_at, timezone.utc).strftime("%a %b %d %H:%M:%S %Y"),
            datetime.fromtimestamp(created_at).strftime("%a %b %d %H:%M:%S %Y"),
        }
        stat_path = Path(f"""/proc/{pid}/stat""")
        if stat_path.is_file():
            # Linux: Claude records stat field 22 (start ticks since boot); count after the parenthesised process name.
            starts.add(stat_path.read_text(encoding="utf-8").rpartition(")")[2].split()[19])
        if " ".join(recorded_start.split()) not in {" ".join(start.split()) for start in starts}:
            raise ValueError("Claude PID metadata process start conflicts with the live process")
    elif not registered_id:
        raise ValueError("Claude PID metadata has no process start identity and the session manager has no registered conversation ID")
    session_id = conversation_id(value=metadata.get("sessionId"))
    if registered_id and conversation_id(value=registered_id) != session_id:
        raise ValueError("Registered conversation ID conflicts with live Claude PID metadata")
    return session_id, ()


def claude_transcript_paths(*, home: Path, session_id: str) -> tuple[Path, ...]:
    root = readable_status_path(path=home / "projects")
    paths = tuple(readable_status_path(path=path) for path in root.rglob(f"""{session_id}.jsonl"""))
    if len(paths) != 1:
        raise ValueError(f"""Claude conversation ID resolved to {len(paths)} transcripts; expected one""")
    return paths


def codex_transcript_paths(
    *, paths: tuple[Path, ...], home: Path, registered_id: str
) -> tuple[str, tuple[Path, ...], tuple[str, ...]]:
    session_id = conversation_id(value=registered_id) if registered_id else ""
    candidates = set(paths)
    if session_id and not any(path.name.endswith(f"""-{session_id}.jsonl""") for path in candidates):
        root = readable_status_path(path=home / "sessions")
        candidates.update(root.rglob(f"""rollout-*-{session_id}.jsonl"""))
    matches: list[tuple[str, Path]] = []
    limitations: list[str] = []
    for path in sorted(candidates):
        try:
            metadata = codex_transcript_metadata(path=path)
            candidate_id = conversation_id(value=metadata.get("id"))
            if (session_id and candidate_id == session_id) or (not session_id and metadata.get("source") == "cli"):
                matches.append((candidate_id, readable_status_path(path=path)))
        except (OSError, ValueError) as error:
            limitations.append(f"""Cannot validate Codex transcript {path.name}: {error}""")
    if len(matches) != 1:
        limitations.append(f"""Codex process resolved to {len(matches)} matching main transcripts; no transcript was selected.""")
        return session_id, (), tuple(limitations)
    selected_id, selected_path = matches[0]
    child_count = len(candidates) - len(matches)
    if child_count:
        limitations.append(f"""Excluded {child_count} open transcripts that did not match the main conversation.""")
    return selected_id, (selected_path,), tuple(limitations)
