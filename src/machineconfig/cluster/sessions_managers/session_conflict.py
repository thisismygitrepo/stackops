from __future__ import annotations

import json
import subprocess
from typing import Literal, NotRequired, TypedDict, cast


SessionBackend = Literal["zellij", "tmux", "windows-terminal"]
SessionConflictAction = Literal["restart", "rename", "error"]
ConflictSource = Literal["existing", "duplicate"]


class SessionLaunchPlan(TypedDict):
    requested_name: str
    session_name: str
    restart_required: bool
    conflict_source: NotRequired[ConflictSource]


def validate_session_conflict_action(on_conflict: str) -> SessionConflictAction:
    if on_conflict not in {"restart", "rename", "error"}:
        raise ValueError(f"Unsupported on_conflict policy: {on_conflict}")
    return cast(SessionConflictAction, on_conflict)


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
    existing_sessions = list_existing_sessions(backend)
    planned_sessions: set[str] = set()
    plans: list[SessionLaunchPlan] = []

    for requested_name in requested_session_names:
        conflict_with_existing = session_exists(requested_name, existing_sessions, backend)
        conflict_with_planned = session_exists(requested_name, planned_sessions, backend)

        if conflict_with_planned or conflict_with_existing:
            if on_conflict == "error":
                if conflict_with_planned:
                    raise ValueError(
                        f"Duplicate target session '{requested_name}' detected in the selected layouts. "
                        "Use unique layout names or --on-conflict rename."
                    )
                raise ValueError(
                    f"Session '{requested_name}' already exists. "
                    "Use --on-conflict restart or --on-conflict rename."
                )

            if on_conflict == "restart":
                if conflict_with_planned:
                    raise ValueError(
                        f"Duplicate target session '{requested_name}' detected in the selected layouts. "
                        "Use unique layout names or --on-conflict rename."
                    )
                plans.append(
                    {
                        "requested_name": requested_name,
                        "session_name": requested_name,
                        "restart_required": True,
                        "conflict_source": "existing",
                    }
                )
                planned_sessions.add(requested_name)
                continue

            suffix = 1
            reserved_sessions = existing_sessions | planned_sessions
            while True:
                candidate_name = f"{requested_name}_{suffix}"
                if not session_exists(candidate_name, reserved_sessions, backend):
                    plans.append(
                        {
                            "requested_name": requested_name,
                            "session_name": candidate_name,
                            "restart_required": False,
                            "conflict_source": "duplicate" if conflict_with_planned else "existing",
                        }
                    )
                    planned_sessions.add(candidate_name)
                    break
                suffix += 1
            continue

        plans.append(
            {
                "requested_name": requested_name,
                "session_name": requested_name,
                "restart_required": False,
            }
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
