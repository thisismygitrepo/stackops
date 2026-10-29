from collections import Counter
from dataclasses import asdict
from html import escape
import io
import json
import os
from pathlib import Path
import re
import stat
import sys

from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, StatusBackend, StatusFormat, StatusSnapshot


def plain_status_text(value: str) -> str:
    value = re.sub(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))", "", value)
    return "".join(character for character in value if character in "\n\t" or ord(character) >= 32 and ord(character) != 127)


def _markdown(value: str) -> str:
    value = escape(plain_status_text(value), quote=False).replace("\\", "\\\\")
    for character in "`*_[]#!|":
        value = value.replace(character, f"""\\{character}""")
    return value.replace("\r", "").replace("\n", "<br>")


def _brief(value: str) -> str:
    value = " ".join(plain_status_text(value).split())
    return value if len(value) <= 180 else f"""{value[:177]}…"""


def _row(agent: AgentSnapshot, backend: StatusBackend) -> tuple[str, ...]:
    human_count = sum(message.kind == "user" for message in agent.history.messages)
    context_count = sum(message.kind != "user" for message in agent.history.messages)
    pane_reference = f"""{agent.session} / {agent.window_id}""" if agent.tab_id else agent.window_id
    history = f"""{human_count} human messages; {agent.history.coverage}. See {pane_reference} below."""
    if context_count:
        history += f""" {context_count} separately labelled context/event records."""
    if agent.history.omitted_messages:
        history += f""" {agent.history.omitted_messages} earlier records omitted by --messages."""
    workspace = f"""{agent.workspace if agent.workspace is not None else 'unavailable'}: {agent.workspace_name or 'unnamed'}"""
    if agent.workspace_id:
        workspace += f"""\n{agent.workspace_id}"""
    workspace += f"""\nTab: {agent.tab_name or 'unnamed'} [{agent.tab_id}]""" if agent.tab_id else "\nSeparate tab unavailable"
    if backend == "aoe":
        workspace = f"""Group: {agent.workspace_name or 'ungrouped'}"""
    return (
        f"""{agent.session}\n{agent.session_id or 'ID unavailable'}""",
        workspace,
        f"""{agent.window_name}\n{agent.window_id}""",
        f"""{agent.harness or 'unknown'}\n{agent.cwd or 'CWD unavailable'}\nPID {agent.process.pid if agent.process.pid is not None else 'unavailable'}""",
        _brief(agent.task) or "Unknown; see retained evidence",
        history,
        f"""{agent.status}; task: {agent.task_status}\nReported: {agent.reported_state or 'unknown'}""",
        _brief(agent.latest_activity) or "; ".join(agent.evidence) or "Unavailable",
    )


def _appendix(snapshot: StatusSnapshot, markdown: bool) -> list[str]:
    sections: list[str] = []
    for agent in snapshot.agents:
        transform = _markdown if markdown else plain_status_text
        pane_reference = f"""{agent.session} / {agent.window_id}""" if snapshot.backend == "herdr" else agent.window_id
        sections.extend(["", transform(f"""{pane_reference} — {agent.window_name}"""), transform(f"""History: {agent.history.coverage}.""")])
        for number, message in enumerate(agent.history.messages, start=1):
            kind = "human message" if message.kind == "user" else "retained goal context (not an original human message)" if message.kind == "goal_context" else message.kind
            sections.extend(["", transform(f"""{number}. {message.timestamp or 'Timestamp unavailable'} [{kind}] {message.text}""")])
            location = f"""{message.source}:{message.line}""" if message.line is not None else message.source
            sections.append(transform(f"""Source: {location}"""))
        if not agent.history.messages:
            sections.append("No human-message records available in the selected history sources.")
        if agent.history.omitted_messages:
            sections.append(transform(f"""--messages omitted {agent.history.omitted_messages} earlier records."""))
        if agent.latest_activity:
            sections.extend(["", transform(f"""Latest activity/result: {agent.latest_activity}""")])
        if agent.prompt.get("found") or agent.prompt.get("blocked"):
            sections.append(transform(f"""Pending prompt (not answered): {json.dumps(agent.prompt, ensure_ascii=False, default=str)}"""))
        if agent.evidence:
            sections.append(transform(f"""Status evidence: {'; '.join(agent.evidence)}"""))
        if agent.history.sources:
            sections.append(transform(f"""History sources: {'; '.join(agent.history.sources)}"""))
        limitations = tuple(dict.fromkeys((*agent.limitations, *agent.process.limitations, *agent.history.limitations)))
        if limitations:
            sections.append(transform(f"""Limitations: {'; '.join(limitations)}"""))
    return sections


def _coverage_entries(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    entries: list[str] = []
    for entry in value:
        if isinstance(entry, dict):
            identity = " / ".join(str(entry[key]) for key in ("session", "name", "window_id") if entry.get(key))
            reason = entry.get("reason") or entry.get("status") or entry.get("limitation")
            entries.append(f"""{identity or 'Identifiers unavailable'}{f': {_brief(str(reason))}' if reason else ''}""")
        else:
            entries.append(str(entry))
    return tuple(entries)


def status_coverage_lines(snapshot: StatusSnapshot) -> list[str]:
    coverage = snapshot.coverage
    pane_label = "runtimes" if snapshot.backend == "aoe" else "panes" if snapshot.backend == "herdr" else "windows"
    workspace_label = "groups" if snapshot.backend == "aoe" else "workspace records"
    lines = [
        f"""Coverage: {coverage.get('sessions_inspected', '?')}/{coverage.get('live_sessions', '?')} live sessions; """
        f"""{coverage.get('windows_inspected', '?')}/{coverage.get('windows_discovered', '?')} {pane_label} inspected; """
        f"""{coverage.get('workspace_records', '?')} {workspace_label}; """
        f"""{coverage.get('agents_found', len(snapshot.agents))} agents found, {len(snapshot.agents)} shown.""",
    ]
    sessions = coverage.get("sessions")
    if isinstance(sessions, list):
        for session in sessions:
            if isinstance(session, dict):
                attached = "attached" if session.get("attached") is True else "detached" if session.get("attached") is False else "attachment unknown"
                lines.append(f"""Session {session.get('name') or 'unnamed'} [{session.get('id') or 'ID unavailable'}]: {attached}; {session.get('window_count', '?')} {pane_label}.""")
    for key, label in (
        ("saved_sessions_skipped", "Saved sessions skipped" if snapshot.backend == "tuios" else "Stopped sessions skipped"), ("excluded_windows", f"""Excluded {pane_label}"""),
        ("vanished_windows", f"""Disappeared/unavailable {pane_label}"""), ("ambiguous_candidates", "Ambiguous candidates"),
        ("new_windows_not_inspected", f"""New {pane_label} not inspected"""),
    ):
        entries = _coverage_entries(coverage.get(key))
        if entries:
            lines.append(f"""{label} ({len(entries)}): {'; '.join(entries)}""")
    return lines


def render_status(*, snapshot: StatusSnapshot, output_format: StatusFormat) -> str:
    if output_format == "json":
        return json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, default=str) + "\n"
    counts = ", ".join(f"""{name}: {count}""" for name, count in sorted(Counter(agent.status for agent in snapshot.agents).items())) or "no agents"
    match snapshot.backend:
        case "aoe":
            backend_scope = "Local AoE current profile"
            hierarchy = "Hierarchy: AoE group → session → tmux pane or structured worker."
        case "herdr":
            backend_scope = "Local Herdr sessions"
            hierarchy = "Hierarchy: session → workspace → tab → pane."
        case "tuios":
            backend_scope = f"""Local TUIOS daemon: {snapshot.server or 'current/default'}"""
            hierarchy = "Hierarchy: session → workspace → window/pane. Separate tabs/nested panes are unavailable unless reported in evidence."
    introductory = [
        f"""Agent snapshot: {snapshot.observed_at} (inspection began {snapshot.started_at}).""",
        f"""Backend: {snapshot.backend}. {backend_scope}. Reported agents: {len(snapshot.agents)}; {counts}.""",
        hierarchy,
        "Task text comes from retained requests/context; completion is reported evidence, not independently verified success.",
        *status_coverage_lines(snapshot),
    ]
    if snapshot.limitations:
        introductory.append(f"""Coverage limitations: {'; '.join(snapshot.limitations)}""")
    if not snapshot.agents:
        introductory.append("No agents matched the selected scope; see coverage for inspection failures or excluded panes.")
    columns = ("Session", "Group" if snapshot.backend == "aoe" else "Workspace/tab", "Runtime name and ID" if snapshot.backend == "aoe" else "Window/pane name and ID", "Harness and working directory", "Task/request excerpt", "User messages so far", "Current status", "Latest evidence/blocker")
    if output_format == "markdown":
        lines = [_markdown(line) for line in introductory]
        lines.extend(["", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _column in columns) + " |"])
        lines.extend("| " + " | ".join(_markdown(value) for value in _row(agent, backend=snapshot.backend)) + " |" for agent in snapshot.agents)
        return "\n\n".join(lines[:len(introductory)]) + "\n" + "\n".join(lines[len(introductory):] + _appendix(snapshot, markdown=True)) + "\n"
    buffer = io.StringIO()
    console = Console(file=buffer, width=180, force_terminal=False, color_system=None)
    for line in introductory:
        console.print(Text(plain_status_text(line)))
    table = Table(show_lines=True, expand=True)
    for column in columns:
        table.add_column(column, overflow="fold")
    for agent in snapshot.agents:
        table.add_row(*(Text(plain_status_text(value)) for value in _row(agent, backend=snapshot.backend)))
    console.print(table)
    for line in _appendix(snapshot, markdown=False):
        console.print(Text(line))
    return buffer.getvalue()


def write_status_output(*, report: str, output: Path | None, force: bool) -> None:
    if output is None:
        sys.stdout.write(report)
        return
    path = output.expanduser().absolute()
    if path.is_relative_to(Path.home() / "dotfiles") or path.resolve().is_relative_to((Path.home() / "dotfiles").resolve()):
        raise ValueError("The output path is in a restricted directory.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    if not force:
        flags |= os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("--output must name a regular file.")
        os.fchmod(stream.fileno(), 0o600)
        stream.truncate(0)
        stream.write(report)
