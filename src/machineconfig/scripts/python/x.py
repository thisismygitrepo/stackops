
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import subprocess
import tempfile
from typing import Annotated, Literal, TypeAlias

import typer


ReasoningEffort: TypeAlias = Literal["none", "low", "high", "xhigh"]


def resolve_reasoning(shortcut: str) -> ReasoningEffort:
    match shortcut:
        case "n":
            return "none"
        case "l":
            return "low"
        case "h":
            return "high"
        case "x":
            return "xhigh"
        case _:
            raise typer.BadParameter("""reasoning must be one of: n, l, h, x""")


def write_prompt_file(prompt: str) -> Path:
    tmp_root = Path.home().joinpath("tmp_results/tmp_prompts/")
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_root / f"prompt_{id(prompt)}.txt"
    tmp_file.write_text(prompt)
    return tmp_file


def build_command(reasoning_effort: ReasoningEffort, prompt_path: Path) -> list[str]:
    return ["codex", "--dangerously-bypass-approvals-and-sandbox", "exec", "-c", f'model_reasoning_effort="{reasoning_effort}"', str(prompt_path)]


def run_command(command: Sequence[str]) -> int:
    try:
        completed_process = subprocess.run(command, check=False)
    except FileNotFoundError as error:
        filename = error.filename or command[0]
        strerror = error.strerror or "unknown error"
        typer.echo(f"""Failed to execute {filename!r}: {strerror}""", err=True)
        return 1
    return completed_process.returncode



def main(
    reasoning: Annotated[str, typer.Argument(help="n=none, l=low, h=high, x=xhigh")],
    prompt: Annotated[list[str], typer.Argument(help="Prompt text (all remaining words are joined)")],
) -> None:
    prompt_path = write_prompt_file(" ".join(prompt))
    try:
        return_code = run_command(build_command(reasoning_effort=resolve_reasoning(reasoning), prompt_path=prompt_path))
    finally:
        prompt_path.unlink(missing_ok=True)
    raise typer.Exit(code=return_code)


def run():
    app = typer.Typer(add_completion=False, no_args_is_help=True)
    app.command(name="x", help=main.__doc__, short_help="Execute a prompt with codex exec", no_args_is_help=False)(main)
    app()
if __name__ == "__main__":
    run()