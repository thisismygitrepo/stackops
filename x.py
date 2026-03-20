from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
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
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        prefix="codex-exec-",
        delete=False,
    ) as file_handle:
        file_handle.write(prompt)
        file_handle.flush()
        return Path(file_handle.name)


def build_command(reasoning_effort: ReasoningEffort, prompt_path: Path) -> list[str]:
    return ["codex", "exec", "-c", f'model_reasoning_effort="{reasoning_effort}"', str(prompt_path)]


def run_command(command: Sequence[str]) -> int:
    try:
        completed_process = subprocess.run(command, check=False)
    except FileNotFoundError as error:
        filename = error.filename or command[0]
        strerror = error.strerror or "unknown error"
        typer.echo(f"""Failed to execute {filename!r}: {strerror}""", err=True)
        return 1
    return completed_process.returncode


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    reasoning: Annotated[str, typer.Argument(help="n=none, l=low, h=high, x=xhigh")],
    prompt: Annotated[str, typer.Argument(help="Prompt text to write to a temporary .txt file and pass to codex")],
) -> None:
    prompt_path = write_prompt_file(prompt)
    try:
        return_code = run_command(build_command(reasoning_effort=resolve_reasoning(reasoning), prompt_path=prompt_path))
    finally:
        prompt_path.unlink(missing_ok=True)
    raise typer.Exit(code=return_code)


if __name__ == "__main__":
    app()
