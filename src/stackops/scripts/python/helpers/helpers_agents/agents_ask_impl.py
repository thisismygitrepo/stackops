from collections.abc import Sequence
from pathlib import Path
from platform import system
import shlex
import subprocess
import sys
from tempfile import NamedTemporaryFile
from typing import Final, cast, get_args

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort, ReasoningShortcut, resolve_reasoning

ASK_REASONING_AGENTS: Final[tuple[AGENTS, ...]] = ("codex", "copilot", "pi")
_ASK_REASONING_SHORTCUTS: Final[tuple[str, ...]] = cast(tuple[str, ...], get_args(ReasoningShortcut))


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


def _quote_for_shell(value: str, *, is_windows: bool) -> str:
    if is_windows:
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def _build_copilot_ask_command(prompt_file: Path, reasoning_effort: ReasoningEffort | None) -> str:
    is_windows = system() == "Windows"
    prompt_file_q = _quote_for_shell(str(prompt_file), is_windows=is_windows)
    if is_windows:
        prompt_content_expr = f"(Get-Content -Raw {prompt_file_q})"
    else:
        prompt_content_expr = f'"$(cat {prompt_file_q})"'
    reasoning_arg = ""
    if reasoning_effort is not None:
        reasoning_arg = f" --reasoning-effort {reasoning_effort}"
    return f"copilot{reasoning_arg} -p {prompt_content_expr} --yolo"


def build_ask_command(agent: AGENTS, prompt_file: Path, reasoning_effort: ReasoningEffort | None) -> str:
    if reasoning_effort is not None and agent not in ASK_REASONING_AGENTS:
        raise ValueError("--reasoning is only supported for --agent codex, --agent copilot, or --agent pi")
    if agent == "copilot":
        return _build_copilot_ask_command(prompt_file=prompt_file, reasoning_effort=reasoning_effort)
    return build_agent_command(agent=agent, prompt_file=prompt_file, reasoning_effort=reasoning_effort)


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


def _split_legacy_ask_reasoning(
    agent: AGENTS, reasoning: ReasoningShortcut | None, prompt_parts: Sequence[str]
) -> tuple[ReasoningShortcut | None, list[str]]:
    normalized_prompt_parts = list(prompt_parts)
    if reasoning is not None:
        return reasoning, normalized_prompt_parts
    if agent not in ASK_REASONING_AGENTS:
        return None, normalized_prompt_parts
    if len(normalized_prompt_parts) <= 1:
        return None, normalized_prompt_parts
    first_prompt_part = normalized_prompt_parts[0]
    if first_prompt_part not in _ASK_REASONING_SHORTCUTS:
        return None, normalized_prompt_parts
    return cast(ReasoningShortcut, first_prompt_part), normalized_prompt_parts[1:]


def _resolve_ask_reasoning(agent: AGENTS, reasoning: ReasoningShortcut | None) -> ReasoningEffort | None:
    if reasoning is None:
        return None
    if agent not in ASK_REASONING_AGENTS:
        raise ValueError("--reasoning is only supported for --agent codex, --agent copilot, or --agent pi")
    return resolve_reasoning(shortcut=reasoning, agent=agent)


def _format_ask_reasoning(reasoning_shortcut: ReasoningShortcut | None, reasoning_effort: ReasoningEffort | None) -> str:
    match reasoning_shortcut, reasoning_effort:
        case None, None:
            return "agent default"
        case shortcut, effort if shortcut is not None and effort is not None:
            return f"{effort} ({shortcut})"
        case _, effort if effort is not None:
            return effort
        case _:
            return "agent default"


def _print_ask_summary(
    *,
    agent: AGENTS,
    reasoning_shortcut: ReasoningShortcut | None,
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
    table.add_row("Reasoning", Text(_format_ask_reasoning(reasoning_shortcut=reasoning_shortcut, reasoning_effort=reasoning_effort)))
    table.add_row("Prompt", Text(f"{len(prompt_text)} chars, {prompt_text.count('\n') + 1} lines"))
    table.add_row("File prompt", Text("none" if file_prompt is None else str(file_prompt.expanduser().resolve())))
    table.add_row("Temp prompt", Text(str(prompt_path)))
    table.add_row("Command", Text(command_line))

    console = Console()
    console.print(Panel(table, title="Agent Ask", border_style="blue"))
    console.rule("[bold blue]Agent Output")


def run_ask(*, prompt_parts: Sequence[str], agent: AGENTS, reasoning: ReasoningShortcut | None, file_prompt: Path | None, quiet: bool) -> int:
    reasoning_shortcut, normalized_prompt_parts = _split_legacy_ask_reasoning(agent=agent, reasoning=reasoning, prompt_parts=prompt_parts)
    reasoning_effort = _resolve_ask_reasoning(agent=agent, reasoning=reasoning_shortcut)
    prompt_text = _compose_ask_prompt_text(prompt_parts=normalized_prompt_parts, file_prompt=file_prompt)
    prompt_path = _write_temporary_prompt_file(prompt_text=prompt_text)
    try:
        command_line = build_ask_command(agent=agent, prompt_file=prompt_path, reasoning_effort=reasoning_effort)
        if not quiet:
            _print_ask_summary(
                agent=agent,
                reasoning_shortcut=reasoning_shortcut,
                reasoning_effort=reasoning_effort,
                prompt_text=prompt_text,
                file_prompt=file_prompt,
                prompt_path=prompt_path,
                command_line=command_line,
            )
        return run_shell_command(command_line=command_line)
    finally:
        prompt_path.unlink(missing_ok=True)
