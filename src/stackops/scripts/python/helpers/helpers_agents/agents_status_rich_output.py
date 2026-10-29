from collections import Counter
from datetime import datetime
import io
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import AgentSnapshot, StatusSnapshot
from stackops.scripts.python.helpers.helpers_agents.agents_status_render import plain_status_text, status_coverage_lines, write_status_output


def _status_text(status: str) -> Text:
    colours = {
        "working": "bold cyan", "waiting": "bold yellow", "blocked": "bold red",
        "idle": "green", "completed": "bold green", "failed": "bold red",
        "unknown": "yellow", "unavailable": "dim",
    }
    return Text(plain_status_text(status.upper()), style=colours.get(status, "white"))


def _history(agent: AgentSnapshot) -> Group:
    human_count = sum(message.kind == "user" for message in agent.history.messages)
    heading = Text(f"""History · {human_count} human messages · {agent.history.coverage}""", style="bold yellow")
    timeline = Table.grid(padding=(0, 2), expand=True)
    timeline.add_column(width=22, no_wrap=False)
    timeline.add_column(ratio=1, overflow="fold")
    for number, message in enumerate(agent.history.messages, start=1):
        try:
            stamp = datetime.fromisoformat(message.timestamp).astimezone().strftime("%d %b %H:%M:%S")
        except ValueError:
            stamp = message.timestamp or "Time unavailable"
        label = Text(f"""{number}. {plain_status_text(stamp)}""", style="dim")
        label.append("\nHuman" if message.kind == "user" else "\nGoal context · not original" if message.kind == "goal_context" else f"""\n{plain_status_text(message.kind)}""", style="cyan" if message.kind == "user" else "yellow")
        content = Text(plain_status_text(message.text), overflow="fold")
        if message.line is not None:
            content.append(f"""\nSource line {message.line}""", style="dim")
        timeline.add_row(label, content)
        timeline.add_row("", "")
    if not agent.history.messages:
        timeline.add_row("", Text("History extraction disabled." if agent.history.coverage == "disabled" else "No human-message records available.", style="dim"))
    if agent.history.omitted_messages:
        timeline.add_row("", Text(f"""{agent.history.omitted_messages} earlier records omitted by --messages.""", style="yellow"))
    return Group(heading, timeline)


def _agent_card(agent: AgentSnapshot) -> Panel:
    fields = Table.grid(padding=(0, 2), expand=True)
    fields.add_column(style="bold", width=11)
    fields.add_column(ratio=1, overflow="fold")
    workspace = agent.workspace_name or (str(agent.workspace) if agent.workspace is not None else "unavailable")
    location = f"""{agent.session} / {workspace}"""
    if agent.tab_id:
        location += f""" / {agent.tab_name or agent.tab_id}"""
    if agent.workspace_id:
        location += f"""\nWorkspace ID: {agent.workspace_id}"""
    if agent.tab_id:
        location += f"""\nTab ID: {agent.tab_id}"""
    fields.add_row("Location", Text(plain_status_text(location)))
    fields.add_row("Harness", Text(plain_status_text(f"""{agent.harness} · PID {agent.process.pid if agent.process.pid is not None else 'unknown'}""")))
    fields.add_row("Directory", Text(plain_status_text(agent.cwd or "unavailable"), style="dim"))
    fields.add_row("Task", Text(plain_status_text(agent.task)))
    fields.add_row("Latest", Text(plain_status_text(agent.latest_activity)))
    fields.add_row("Task state", Text(plain_status_text(f"""{agent.task_status} · reported agent state: {agent.reported_state or 'unknown'}""")))
    sections: list[Table | Text | Group | Panel] = [fields, Text(), _history(agent)]
    if agent.prompt.get("found") or agent.prompt.get("blocked"):
        lines = agent.prompt.get("lines")
        prompt = "\n".join(line for line in lines if isinstance(line, str)) if isinstance(lines, list) else ""
        if not prompt:
            message = agent.prompt.get("message") or agent.prompt.get("reason")
            prompt = message if isinstance(message, str) and message else "The agent reports pending input; question text is unavailable."
        sections.extend([Text(), Panel(Text(plain_status_text(prompt)), title=Text("Pending input · unanswered"), border_style="yellow")])
    if agent.evidence:
        sections.extend([Text(), Text(plain_status_text("Evidence: " + " ".join(agent.evidence)), style="dim")])
    if agent.history.sources:
        sections.append(Text(plain_status_text("Sources: " + "; ".join(agent.history.sources)), style="dim"))
    limitations = tuple(dict.fromkeys((*agent.limitations, *agent.history.limitations, *agent.process.limitations)))
    if limitations:
        notes = Text("Limitations", style="bold yellow")
        for limitation in limitations:
            notes.append(f"""\n• {plain_status_text(limitation)}""", style="yellow")
        sections.extend([Text(), notes])
    title = _status_text(agent.status)
    title.append(f"""  {plain_status_text(agent.window_name or agent.harness)}""", style="bold")
    return Panel(
        Group(*sections), title=title, title_align="left", border_style=_status_text(agent.status).style,
        subtitle=Text(plain_status_text(f"""{agent.session} / {agent.window_id}"""), style="dim"), subtitle_align="left", padding=(1, 2),
    )


def _show_rich_status(*, snapshot: StatusSnapshot, console: Console) -> None:
    counts = Counter(agent.status for agent in snapshot.agents)
    totals = Text(f"""{len(snapshot.agents)} {'agent' if len(snapshot.agents) == 1 else 'agents'}""", style="bold")
    for status, count in sorted(counts.items()):
        totals.append("    ")
        totals.append_text(_status_text(status))
        totals.append(f""" {count}""")
    try:
        observed = datetime.fromisoformat(snapshot.observed_at).astimezone().strftime("%d %b %Y · %H:%M:%S %Z")
    except ValueError:
        observed = snapshot.observed_at
    coverage = status_coverage_lines(snapshot)
    console.print(Panel(
        Group(totals, Text(plain_status_text(f"""{snapshot.backend.upper()} · {observed}"""), style="dim"), Text(plain_status_text(coverage[0]))),
        title=Text("Agent status", style="bold"), title_align="left", border_style="blue", padding=(1, 2),
    ))
    if console.width >= 100 and snapshot.agents:
        overview = Table(box=box.SIMPLE_HEAVY, expand=True, padding=(0, 1))
        overview.add_column("Status", width=12)
        overview.add_column("Agent", ratio=2, overflow="fold")
        overview.add_column("Location", ratio=1, overflow="fold")
        overview.add_column("Task", ratio=3, overflow="fold", max_width=65)
        for agent in snapshot.agents:
            task = " ".join(plain_status_text(agent.task).split())
            task_excerpt = task[:157] + "…" if len(task) > 160 else task
            overview.add_row(
                _status_text(agent.status), Text(plain_status_text(agent.window_name or agent.harness)),
                Text(plain_status_text(f"""{agent.session} / {agent.workspace_name or agent.workspace or 'unavailable'}""")), Text(task_excerpt),
            )
        console.print(overview)
        console.print(Text("Task excerpts above; retained requests and evidence follow.", style="dim"))
    if not snapshot.agents:
        console.print(Panel(Text("No agents matched this snapshot. See coverage notes for exclusions or inspection gaps."), border_style="yellow"))
    for agent in snapshot.agents:
        console.print()
        console.print(_agent_card(agent))
    notes = [*coverage[1:], *snapshot.limitations]
    if notes:
        console.print()
        console.print(Panel(Text(plain_status_text("\n".join(notes)), style="dim"), title=Text("Coverage notes"), title_align="left", border_style="dim"))


def print_rich_status(*, snapshot: StatusSnapshot, output: Path | None, force: bool) -> None:
    if output is None:
        _show_rich_status(snapshot=snapshot, console=Console(highlight=False))
        return
    buffer = io.StringIO()
    _show_rich_status(snapshot=snapshot, console=Console(file=buffer, width=120, force_terminal=False, color_system=None, highlight=False))
    write_status_output(report=buffer.getvalue(), output=output, force=force)
