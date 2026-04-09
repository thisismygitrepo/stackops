

import json
import subprocess
from typing import Literal, NotRequired, TypedDict


SessionBackend = Literal["zellij", "tmux", "windows-terminal"]
SessionConflictActionLoose = Literal[
    "restart", "r",
    "rename", "n",
    "error", "e",
    "mergeNewWindowsOverwriteMatchingWindows", "m",
    "mergeNewWindowsSkipMatchingWindows", "s",
]
SessionConflictAction = Literal[
    "restart",
    "rename",
    "error",
    "mergeNewWindowsOverwriteMatchingWindows",
    "mergeNewWindowsSkipMatchingWindows",
]
SessionConflictActionLoose2Strict: dict[SessionConflictActionLoose, SessionConflictAction] = {
    "restart": "restart",
    "r": "restart",
    "rename": "rename",
    "n": "rename",
    "error": "error",
    "e": "error",
    "mergeNewWindowsOverwriteMatchingWindows": "mergeNewWindowsOverwriteMatchingWindows",
    "m": "mergeNewWindowsOverwriteMatchingWindows",
    "mergeNewWindowsSkipMatchingWindows": "mergeNewWindowsSkipMatchingWindows",
    "s": "mergeNewWindowsSkipMatchingWindows",
}

ConflictSource = Literal["existing", "duplicate"]
SUPPORTED_SESSION_CONFLICT_ACTIONS = frozenset(
    {
        "restart",
        "rename",
        "error",
        "mergeNewWindowsOverwriteMatchingWindows",
        "mergeNewWindowsSkipMatchingWindows",
    }
)
MERGE_NEW_WINDOWS_SESSION_CONFLICT_ACTIONS = frozenset(
    {
        "mergeNewWindowsOverwriteMatchingWindows",
        "mergeNewWindowsSkipMatchingWindows",
    }
)
MERGE_NEW_WINDOWS_SUPPORTED_BACKENDS = frozenset({"tmux", "windows-terminal"})


class SessionLaunchPlan(TypedDict):
    requested_name: str
    session_name: str
    restart_required: bool
    conflict_source: NotRequired[ConflictSource]
    skip_launch: NotRequired[bool]



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
    if backend in MERGE_NEW_WINDOWS_SUPPORTED_BACKENDS:
        return (
            "Use --on-conflict restart, --on-conflict rename, "
            "--on-conflict mergeNewWindowsOverwriteMatchingWindows, or "
            "--on-conflict mergeNewWindowsSkipMatchingWindows."
        )
    return "Use --on-conflict restart or --on-conflict rename."


def _duplicate_conflict_hint(backend: SessionBackend) -> str:
    if backend in MERGE_NEW_WINDOWS_SUPPORTED_BACKENDS:
        return (
            "Use unique layout names, --on-conflict rename, "
            "--on-conflict mergeNewWindowsOverwriteMatchingWindows, or "
            "--on-conflict mergeNewWindowsSkipMatchingWindows."
        )
    return "Use unique layout names or --on-conflict rename."


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

        if backend == "zellij":
            result = subprocess.run(
                ["zellij", "list-sessions"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return set()
            sessions: set[str] = set()
            for line in result.stdout.splitlines():
                cleaned = line.strip()
                if not cleaned:
                    continue
                sessions.add(cleaned.split()[0])
            return sessions

        if backend == "windows-terminal":
            from machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers import POWERSHELL_CMD

            ps_script = """
Get-Process -Name 'WindowsTerminal' -ErrorAction SilentlyContinue |
Select-Object MainWindowTitle |
ConvertTo-Json -Depth 2
"""
            result = subprocess.run(
                [POWERSHELL_CMD, "-Command", ps_script],
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
            if not isinstance(payload, list):
                payload = [payload]
            titles = {
                str(item.get("MainWindowTitle", "")).strip()
                for item in payload
                if isinstance(item, dict) and str(item.get("MainWindowTitle", "")).strip()
            }
            return titles
    except Exception:
        return set()

    return set()


def session_exists(session_name: str, existing_sessions: set[str], backend: SessionBackend) -> bool:
    if backend != "windows-terminal":
        return session_name in existing_sessions
    session_name_lc = session_name.casefold()
    return any(
        candidate.casefold() == session_name_lc or session_name_lc in candidate.casefold()
        for candidate in existing_sessions
    )


def build_session_launch_plan(
    requested_session_names: list[str],
    backend: SessionBackend,
    on_conflict: SessionConflictAction,
) -> list[SessionLaunchPlan]:
    if (
        on_conflict in MERGE_NEW_WINDOWS_SESSION_CONFLICT_ACTIONS
        and backend not in MERGE_NEW_WINDOWS_SUPPORTED_BACKENDS
    ):
        supported_backends_text = ", ".join(sorted(MERGE_NEW_WINDOWS_SUPPORTED_BACKENDS))
        raise ValueError(
            f"{on_conflict} is only supported for {supported_backends_text} backends."
        )
    existing_sessions = list_existing_sessions(backend)
    planned_sessions: set[str] = set()
    restarted_sessions: set[str] = set()
    plans: list[SessionLaunchPlan] = []

    for requested_name in requested_session_names:
        conflict_with_existing = session_exists(requested_name, existing_sessions, backend)
        conflict_with_planned = session_exists(requested_name, planned_sessions, backend)
        conflict_source = _build_conflict_source(
            conflict_with_existing=conflict_with_existing,
            conflict_with_planned=conflict_with_planned,
        )

        match on_conflict:
            case "mergeNewWindowsOverwriteMatchingWindows":
                should_restart_existing = (
                    backend == "windows-terminal"
                    and conflict_with_existing
                    and requested_name not in restarted_sessions
                )
                if should_restart_existing:
                    restarted_sessions.add(requested_name)
                plans.append(
                    _build_launch_plan(
                        requested_name=requested_name,
                        session_name=requested_name,
                        restart_required=should_restart_existing,
                        conflict_source=conflict_source,
                        skip_launch=False,
                    )
                )
                planned_sessions.add(requested_name)
                continue
            case "mergeNewWindowsSkipMatchingWindows":
                if backend == "windows-terminal" and conflict_with_existing:
                    plans.append(
                        _build_launch_plan(
                            requested_name=requested_name,
                            session_name=requested_name,
                            restart_required=False,
                            conflict_source="existing",
                            skip_launch=True,
                        )
                    )
                    continue
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
            case "error":
                if conflict_with_planned:
                    raise ValueError(
                        f"Duplicate target session '{requested_name}' detected in the selected layouts. "
                        f"{_duplicate_conflict_hint(backend)}"
                    )
                if conflict_with_existing:
                    raise ValueError(
                        f"Session '{requested_name}' already exists. "
                        f"{_existing_conflict_hint(backend)}"
                    )
            case "restart":
                if conflict_with_planned:
                    raise ValueError(
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
                raise ValueError(f"Unsupported on_conflict policy: {on_conflict}")

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

        if backend == "zellij":
            subprocess.run(
                ["zellij", "delete-session", "--force", session_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return

        if backend == "windows-terminal":
            from machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers import POWERSHELL_CMD

            safe_name = session_name.replace("'", "''")
            ps_script = f"""
$name = '{safe_name}'
Get-Process -Name 'WindowsTerminal' -ErrorAction SilentlyContinue |
Where-Object {{ $_.MainWindowTitle -like "*$name*" }} |
Stop-Process -Force -ErrorAction SilentlyContinue
"""
            subprocess.run(
                [POWERSHELL_CMD, "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
    except Exception:
        return
