

import json
import subprocess
from typing import Literal, NotRequired, TypedDict


SessionBackend = Literal["tmux", "herdr"]
SessionConflictActionLoose = Literal[
    "restart", "r",
    "rename", "n",
    "error", "e",
    "skip", "s",
    "mergeOverwrite", "m",
    "mergeSkip", "M",
]
SessionConflictAction = Literal[
    "restart",
    "rename",
    "error",
    "skip",
    "mergeOverwrite",
    "mergeSkip",
]
SessionConflictActionLoose2Strict: dict[SessionConflictActionLoose, SessionConflictAction] = {
    "restart": "restart",
    "r": "restart",
    "rename": "rename",
    "n": "rename",
    "error": "error",
    "e": "error",
    "skip": "skip",
    "s": "skip",
    "mergeOverwrite": "mergeOverwrite",
    "m": "mergeOverwrite",
    "mergeSkip": "mergeSkip",
    "M": "mergeSkip",
}

ConflictSource = Literal["existing", "duplicate"]
SUPPORTED_SESSION_CONFLICT_ACTIONS = frozenset(
    {
        "restart",
        "rename",
        "error",
        "skip",
        "mergeOverwrite",
        "mergeSkip",
    }
)
MERGE_SESSION_CONFLICT_ACTIONS = frozenset(
    {
        "mergeOverwrite",
        "mergeSkip",
    }
)
MERGE_SUPPORTED_BACKENDS = frozenset({"tmux"})


class SessionLaunchPlan(TypedDict):
    requested_name: str
    session_name: str
    restart_required: bool
    conflict_source: NotRequired[ConflictSource]
    skip_launch: NotRequired[bool]


class SessionConflictError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)



def _build_conflict_source(
    conflict_with_existing: bool,
    conflict_with_planned: bool,
) -> ConflictSource | None:
    if conflict_with_planned:
        return "duplicate"
    if conflict_with_existing:
        return "existing"
    return None


def _build_launch_plan(
    requested_name: str,
    session_name: str,
    restart_required: bool,
    conflict_source: ConflictSource | None,
    skip_launch: bool,
) -> SessionLaunchPlan:
    plan: SessionLaunchPlan = {
        "requested_name": requested_name,
        "session_name": session_name,
        "restart_required": restart_required,
    }
    if conflict_source is not None:
        plan["conflict_source"] = conflict_source
    if skip_launch:
        plan["skip_launch"] = True
    return plan


def _existing_conflict_hint(backend: SessionBackend) -> str:
    if backend in MERGE_SUPPORTED_BACKENDS:
        return (
            "Use --on-conflict restart, --on-conflict rename, --on-conflict skip, "
            "--on-conflict mergeOverwrite, or "
            "--on-conflict mergeSkip."
        )
    return "Use --on-conflict restart, --on-conflict rename, or --on-conflict skip."


def _duplicate_conflict_hint(backend: SessionBackend) -> str:
    if backend in MERGE_SUPPORTED_BACKENDS:
        return (
            "Use unique layout names, --on-conflict rename, --on-conflict skip, "
            "--on-conflict mergeOverwrite, or "
            "--on-conflict mergeSkip."
        )
    return "Use unique layout names, --on-conflict rename, or --on-conflict skip."


def list_existing_sessions(backend: SessionBackend) -> set[str]:
    try:
        if backend == "tmux":
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").lower()
                if "no server running" in stderr:
                    return set()
                return set()
            return {line.strip() for line in result.stdout.splitlines() if line.strip()}

        if backend == "herdr":
            result = subprocess.run(
                ["herdr", "workspace", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return set()
            output = result.stdout.strip()
            if not output:
                return set()
            payload = json.loads(output)
            result_payload = payload.get("result") if isinstance(payload, dict) else None
            if not isinstance(result_payload, dict):
                return set()
            workspaces = result_payload.get("workspaces")
            if not isinstance(workspaces, list):
                return set()
            return {
                str(item.get("label", "")).strip()
                for item in workspaces
                if isinstance(item, dict) and str(item.get("label", "")).strip()
            }
    except Exception:
        return set()

    return set()


def session_exists(session_name: str, existing_sessions: set[str], backend: SessionBackend) -> bool:
    return session_name in existing_sessions


def build_session_launch_plan(
    requested_session_names: list[str],
    backend: SessionBackend,
    on_conflict: SessionConflictAction,
) -> list[SessionLaunchPlan]:
    if (
        on_conflict in MERGE_SESSION_CONFLICT_ACTIONS
        and backend not in MERGE_SUPPORTED_BACKENDS
    ):
        supported_backends_text = ", ".join(sorted(MERGE_SUPPORTED_BACKENDS))
        raise SessionConflictError(
            f"{on_conflict} is only supported for {supported_backends_text} backends."
        )
    existing_sessions = list_existing_sessions(backend)
    planned_sessions: set[str] = set()
    plans: list[SessionLaunchPlan] = []

    for requested_name in requested_session_names:
        conflict_with_existing = session_exists(requested_name, existing_sessions, backend)
        conflict_with_planned = session_exists(requested_name, planned_sessions, backend)
        conflict_source = _build_conflict_source(
            conflict_with_existing=conflict_with_existing,
            conflict_with_planned=conflict_with_planned,
        )

        match on_conflict:
            case "mergeOverwrite":
                plans.append(
                    _build_launch_plan(
                        requested_name=requested_name,
                        session_name=requested_name,
                        restart_required=False,
                        conflict_source=conflict_source,
                        skip_launch=False,
                    )
                )
                planned_sessions.add(requested_name)
                continue
            case "mergeSkip":
                plans.append(
                    _build_launch_plan(
                        requested_name=requested_name,
                        session_name=requested_name,
                        restart_required=False,
                        conflict_source=conflict_source,
                        skip_launch=False,
                    )
                )
                planned_sessions.add(requested_name)
                continue
            case "skip":
                if conflict_with_existing or conflict_with_planned:
                    plans.append(
                        _build_launch_plan(
                            requested_name=requested_name,
                            session_name=requested_name,
                            restart_required=False,
                            conflict_source=conflict_source,
                            skip_launch=True,
                        )
                    )
                    continue
            case "error":
                if conflict_with_planned:
                    raise SessionConflictError(
                        f"Duplicate target session '{requested_name}' detected in the selected layouts. "
                        f"{_duplicate_conflict_hint(backend)}"
                    )
                if conflict_with_existing:
                    raise SessionConflictError(
                        f"Session '{requested_name}' already exists. "
                        f"{_existing_conflict_hint(backend)}"
                    )
            case "restart":
                if conflict_with_planned:
                    raise SessionConflictError(
                        f"Duplicate target session '{requested_name}' detected in the selected layouts. "
                        f"{_duplicate_conflict_hint(backend)}"
                    )
                if conflict_with_existing:
                    plans.append(
                        _build_launch_plan(
                            requested_name=requested_name,
                            session_name=requested_name,
                            restart_required=True,
                            conflict_source="existing",
                            skip_launch=False,
                        )
                    )
                    planned_sessions.add(requested_name)
                    continue
            case "rename":
                if conflict_with_planned or conflict_with_existing:
                    suffix = 1
                    reserved_sessions = existing_sessions | planned_sessions
                    while True:
                        candidate_name = f"{requested_name}_{suffix}"
                        if not session_exists(candidate_name, reserved_sessions, backend):
                            plans.append(
                                _build_launch_plan(
                                    requested_name=requested_name,
                                    session_name=candidate_name,
                                    restart_required=False,
                                    conflict_source=conflict_source,
                                    skip_launch=False,
                                )
                            )
                            planned_sessions.add(candidate_name)
                            break
                        suffix += 1
                    continue
            case _:
                raise SessionConflictError(f"Unsupported on_conflict policy: {on_conflict}")

        plans.append(
            _build_launch_plan(
                requested_name=requested_name,
                session_name=requested_name,
                restart_required=False,
                conflict_source=None,
                skip_launch=False,
            )
        )
        planned_sessions.add(requested_name)

    return plans


def kill_existing_session(backend: SessionBackend, session_name: str) -> None:
    try:
        if backend == "tmux":
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return

        if backend == "herdr":
            result = subprocess.run(
                ["herdr", "workspace", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return
            output = result.stdout.strip()
            if not output:
                return
            payload = json.loads(output)
            result_payload = payload.get("result") if isinstance(payload, dict) else None
            if not isinstance(result_payload, dict):
                return
            workspaces = result_payload.get("workspaces")
            if not isinstance(workspaces, list):
                return
            for item in workspaces:
                if not isinstance(item, dict):
                    continue
                if str(item.get("label", "")).strip() != session_name:
                    continue
                workspace_id = str(item.get("workspace_id", "")).strip()
                if workspace_id == "":
                    continue
                subprocess.run(
                    ["herdr", "workspace", "close", workspace_id],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
    except Exception:
        return
