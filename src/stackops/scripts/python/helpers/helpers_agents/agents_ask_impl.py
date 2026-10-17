from collections.abc import Sequence
from pathlib import Path
from platform import system
import subprocess
import sys
from tempfile import NamedTemporaryFile

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import (
    ReasoningEffort,
    normalize_reasoning_effort,
)


def _join_prompt_parts(prompt_parts: Sequence[str]) -> str:
    prompt_text = " ".join(prompt_parts).strip()
    if prompt_text == "":
        raise ValueError("""prompt must not be empty""")
    return prompt_text


def _resolve_prompt_path(prompt_path: Path) -> Path:
    prompt_path = prompt_path.expanduser().resolve()
    if not prompt_path.is_file():
        raise ValueError(f"""prompt file does not exist: {prompt_path}""")
    return prompt_path


def _read_prompt_file_text(prompt_path: Path) -> str:
    try:
        return prompt_path.read_text(encoding="utf-8")
    except OSError as error:
        strerror = error.strerror or "unknown error"
        raise ValueError(f"""failed to read prompt file {str(prompt_path)!r}: {strerror}""") from error


def _compose_ask_prompt_text(prompt_parts: Sequence[str], file_prompt: Path | None) -> str:
    prompt_text = _join_prompt_parts(prompt_parts=prompt_parts)
    if file_prompt is None:
        return prompt_text
    resolved_prompt_path = _resolve_prompt_path(prompt_path=file_prompt)
    prompt_file_text = _read_prompt_file_text(prompt_path=resolved_prompt_path)
    return f"""{prompt_text}

--- BEGIN FILE {resolved_prompt_path} ---
{prompt_file_text}
--- END FILE {resolved_prompt_path} ---"""


def build_ask_command(agent: AGENTS, prompt_file: Path, reasoning_effort: ReasoningEffort | None) -> str:
    normalized_reasoning_effort = normalize_reasoning_effort(agent=agent, reasoning_effort=reasoning_effort)
    return build_agent_command(agent=agent, prompt_file=prompt_file, reasoning_effort=normalized_reasoning_effort)


def _run_subprocess(command: Sequence[str], stdin_text: str | None) -> int:
    try:
        completed_process = subprocess.run(command, check=False, input=stdin_text, text=stdin_text is not None)
    except FileNotFoundError as error:
        filename = error.filename or command[0]
        strerror = error.strerror or "unknown error"
        print(f"""Failed to execute {filename!r}: {strerror}""", file=sys.stderr)
        return 1
    return completed_process.returncode


def run_shell_command(command_line: str) -> int:
    if system() == "Windows":
        return _run_subprocess(command=["powershell", "-NoProfile", "-Command", command_line], stdin_text=None)
    return _run_subprocess(command=["bash", "-lc", command_line], stdin_text=None)


def _write_temporary_prompt_file(prompt_text: str) -> Path:
    with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", prefix="agents_ask_", delete=False) as prompt_file:
        prompt_file.write(prompt_text)
        return Path(prompt_file.name)


def _print_ask_summary(
    *,
    agent: AGENTS,
    reasoning_effort: ReasoningEffort | None,
    prompt_text: str,
    file_prompt: Path | None,
    prompt_path: Path,
    command_line: str,
) -> None:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white", overflow="fold")
    table.add_row("Agent", Text(agent))
    table.add_row("Reasoning", Text(reasoning_effort if reasoning_effort is not None else "agent default"))
    table.add_row("Prompt", Text(f"{len(prompt_text)} chars, {prompt_text.count('\n') + 1} lines"))
    table.add_row("File prompt", Text("none" if file_prompt is None else str(file_prompt.expanduser().resolve())))
    table.add_row("Temp prompt", Text(str(prompt_path)))
    table.add_row("Command", Text(command_line))

    console = Console()
    console.print(Panel(table, title="Agent Ask", border_style="blue"))
    console.rule("[bold blue]Agent Output")


def run_ask(*, prompt_parts: Sequence[str], agent: AGENTS, reasoning: ReasoningEffort | None, prompt_path: Path | None, quiet: bool) -> int:
    reasoning_effort = normalize_reasoning_effort(agent=agent, reasoning_effort=reasoning)
    prompt_text = _compose_ask_prompt_text(prompt_parts=prompt_parts, file_prompt=prompt_path)
    temporary_prompt_path = _write_temporary_prompt_file(prompt_text=prompt_text)
    try:
        command_line = build_ask_command(agent=agent, prompt_file=temporary_prompt_path, reasoning_effort=reasoning_effort)
        if not quiet:
            _print_ask_summary(
                agent=agent,
                reasoning_effort=reasoning_effort,
                prompt_text=prompt_text,
                file_prompt=prompt_path,
                prompt_path=temporary_prompt_path,
                command_line=command_line,
            )
        return run_shell_command(command_line=command_line)
    finally:
        temporary_prompt_path.unlink(missing_ok=True)
