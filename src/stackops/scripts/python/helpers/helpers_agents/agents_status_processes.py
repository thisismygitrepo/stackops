from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

import psutil

from stackops.scripts.python.helpers.helpers_agents.agents_status_links import (
    claude_session_id,
    claude_transcript_paths,
    codex_transcript_paths,
    readable_status_path,
)
from stackops.scripts.python.helpers.helpers_agents.agents_status_models import ProcessEvidence


@dataclass(frozen=True)
class ProcessMatch:
    process: psutil.Process
    harness: str
    executable: str
    native: bool


def _match_process(*, process: psutil.Process, hint: str) -> ProcessMatch | None:
    name = process.name().casefold()
    executable = process.exe()
    executable_name = Path(executable).name.casefold()
    command = process.cmdline()
    identities = {name, executable_name}
    if command:
        identities.add(Path(command[0]).name.casefold())
    if executable_name in {"node", "nodejs", "bun", "deno", "python", "python3"} and len(command) > 1:
        token = command[1]
        if not token.startswith("-"):
            identities.add(Path(token).name.casefold())
            if "@openai/codex/" in token:
                identities.add("codex")
            if "@anthropic-ai/claude-code/" in token:
                identities.add("claude")
    if identities.intersection({"claude", "claude-code"}) or "/share/claude/versions/" in executable:
        return ProcessMatch(process=process, harness="claude-code", executable=executable, native=executable_name not in {"node", "bun"})
    if "codex" in identities:
        return ProcessMatch(process=process, harness="codex", executable=executable, native=executable_name == "codex")
    if hint and hint in identities:
        return ProcessMatch(process=process, harness=hint, executable=executable, native=True)
    return None


def _select_process(*, matches: list[ProcessMatch]) -> ProcessMatch | None:
    by_pid = {match.process.pid: match for match in matches}
    roots = [match for match in matches if not any(parent.pid in by_pid for parent in match.process.parents())]
    if len(roots) != 1:
        return None
    root = roots[0]
    if root.native:
        return root
    descendants = {child.pid for child in root.process.children(recursive=True)}
    native = [match for match in matches if match.process.pid in descendants and match.native and match.harness == root.harness]
    return native[0] if len(native) == 1 else root if not native else None


def _open_codex_transcripts(*, process: psutil.Process, timeout: float) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    paths: set[Path] = set()
    limitations: list[str] = []
    try:
        paths.update(Path(item.path) for item in process.open_files() if Path(item.path).match("rollout-*.jsonl"))
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess) as error:
        limitations.append(f"""Process open-file metadata unavailable ({type(error).__name__}).""")
    if not paths:
        executable = shutil.which("lsof")
        if executable is None:
            limitations.append("lsof is unavailable; no held-open Codex transcript could be linked.")
        else:
            try:
                result = subprocess.run(
                    [executable, "-a", "-p", str(process.pid), "-Fn"], capture_output=True, text=True, timeout=timeout, check=False
                )
                if result.returncode:
                    limitations.append(f"""lsof could not read process metadata (exit {result.returncode}).""")
                for line in result.stdout.splitlines():
                    if line.startswith("n") and Path(line[1:]).match("rollout-*.jsonl"):
                        paths.add(Path(line[1:]))
            except (OSError, subprocess.TimeoutExpired) as error:
                limitations.append(f"""lsof process inspection failed ({type(error).__name__}).""")
    return tuple(sorted(paths)), tuple(limitations)


def inspect_processes(
    *, root_pid: int, harness_hint: str, agent_session_id: str, cwd: str, claude_home: Path, codex_home: Path, timeout: float
) -> ProcessEvidence:
    limitations: list[str] = []
    inspected_pid = root_pid
    if root_pid <= 0:
        return ProcessEvidence(
            pid=None, live=None, harness=harness_hint, cwd=cwd, command="", session_id=agent_session_id, transcript_paths=(),
            limitations=("The session manager did not expose a process identifier; process-based transcript linkage is unavailable.",),
        )
    hint = "claude-code" if harness_hint in {"claude", "claude-code"} else harness_hint
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
        matches: list[ProcessMatch] = []
        for process in processes:
            try:
                match = _match_process(process=process, hint=hint)
                if match is not None:
                    matches.append(match)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as error:
                limitations.append(f"""Process {process.pid} identity unavailable ({type(error).__name__}).""")
        selected = _select_process(matches=matches)
        if selected is None:
            live: bool | None = None
            if not matches and not limitations and hint in {"", "codex", "claude-code"}:
                live = False
                limitations.append("The fully inspected process tree has no matching agent process.")
            elif not matches and hint not in {"", "codex", "claude-code"}:
                limitations.append(f"""The session manager identifies harness {hint}; its process identity could not be established.""")
            else:
                limitations.append(f"""Process tree has {len(matches)} agent candidates without one unambiguous identity.""")
            return ProcessEvidence(
                pid=None, live=live, harness=hint, cwd=cwd, command="", session_id=agent_session_id, transcript_paths=(), limitations=tuple(limitations)
            )
        process = selected.process
        inspected_pid = process.pid
        process_cwd = process.cwd()
        session_id = agent_session_id
        paths: tuple[Path, ...] = ()
        try:
            if selected.harness == "claude-code":
                session_id, metadata_limitations = claude_session_id(
                    home=claude_home, pid=process.pid, cwd=process_cwd, created_at=process.create_time(), registered_id=agent_session_id
                )
                limitations.extend(metadata_limitations)
                paths = claude_transcript_paths(home=claude_home, session_id=session_id)
            elif selected.harness == "codex":
                open_paths, open_limitations = _open_codex_transcripts(process=process, timeout=timeout)
                limitations.extend(open_limitations)
                session_id, paths, link_limitations = codex_transcript_paths(paths=open_paths, home=codex_home, registered_id=agent_session_id)
                limitations.extend(link_limitations)
            else:
                limitations.append(f"""Transcript linkage is not supported for harness {selected.harness}.""")
        except (OSError, ValueError) as error:
            limitations.append(str(error))
        if hint and hint != selected.harness:
            limitations.append(f"""Session-manager harness {hint} conflicts with process harness {selected.harness}.""")
        return ProcessEvidence(
            pid=process.pid, live=process.is_running() and process.status() != psutil.STATUS_ZOMBIE, harness=selected.harness,
            cwd=process_cwd, command=str(readable_status_path(path=Path(selected.executable))), session_id=session_id,
            transcript_paths=paths, limitations=tuple(limitations),
        )
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return ProcessEvidence(
            pid=inspected_pid, live=False, harness=hint, cwd=cwd, command="", session_id=agent_session_id, transcript_paths=(),
            limitations=tuple([*limitations, "Process exited during inspection."]),
        )
    except (psutil.AccessDenied, OSError, ValueError) as error:
        return ProcessEvidence(
            pid=None, live=None, harness=hint, cwd=cwd, command="", session_id=agent_session_id, transcript_paths=(),
            limitations=tuple([*limitations, f"""Process inspection unavailable ({type(error).__name__})."""]),
        )
