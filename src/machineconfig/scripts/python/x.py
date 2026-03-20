from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import subprocess
from typing import Annotated, Literal, TextIO, TypeAlias

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


def join_prompt_parts(prompt_parts: Sequence[str]) -> str:
    prompt_text = " ".join(prompt_parts).strip()
    if prompt_text == "":
        raise typer.BadParameter("""prompt must not be empty""")
    return prompt_text


def resolve_prompt_path(prompt_parts: Sequence[str]) -> Path:
    prompt_path = Path(join_prompt_parts(prompt_parts)).expanduser()
    if not prompt_path.is_file():
        raise typer.BadParameter(f"""prompt file does not exist: {prompt_path}""")
    return prompt_path


def build_exec_prefix(reasoning_effort: ReasoningEffort) -> list[str]:
    return [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
    ]


def build_prompt_command(reasoning_effort: ReasoningEffort, prompt: str) -> list[str]:
    return [*build_exec_prefix(reasoning_effort=reasoning_effort), prompt]


def build_file_prompt_command(reasoning_effort: ReasoningEffort) -> list[str]:
    return [*build_exec_prefix(reasoning_effort=reasoning_effort), "-"]


def _run_subprocess(command: Sequence[str], stdin_handle: TextIO | None) -> int:
    try:
        completed_process = subprocess.run(command, check=False, stdin=stdin_handle)
    except FileNotFoundError as error:
        filename = error.filename or command[0]
        strerror = error.strerror or "unknown error"
        typer.echo(f"""Failed to execute {filename!r}: {strerror}""", err=True)
        return 1
    return completed_process.returncode


def run_command(command: Sequence[str]) -> int:
    return _run_subprocess(command=command, stdin_handle=None)


def run_command_with_prompt_file(command: Sequence[str], prompt_path: Path) -> int:
    try:
        with prompt_path.open(mode="r", encoding="utf-8") as prompt_handle:
            return _run_subprocess(command=command, stdin_handle=prompt_handle)
    except OSError as error:
        strerror = error.strerror or "unknown error"
        typer.echo(f"""Failed to read prompt file {str(prompt_path)!r}: {strerror}""", err=True)
        return 1


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    reasoning: Annotated[str, typer.Argument(help="n=none, l=low, h=high, x=xhigh")],
    prompt: Annotated[
        list[str],
        typer.Argument(help="Prompt text to pass to codex, or a prompt file path when --file-prompt is set"),
    ],
    file_prompt: Annotated[
        bool,
        typer.Option("--file-prompt", "-f", help="Treat PROMPT as a file path and pass its contents to codex via stdin"),
    ] = False,
) -> None:
    reasoning_effort = resolve_reasoning(reasoning)
    if file_prompt:
        prompt_path = resolve_prompt_path(prompt_parts=prompt)
        return_code = run_command_with_prompt_file(
            command=build_file_prompt_command(reasoning_effort=reasoning_effort),
            prompt_path=prompt_path,
        )
        raise typer.Exit(code=return_code)

    prompt_text = join_prompt_parts(prompt_parts=prompt)
    return_code = run_command(
        command=build_prompt_command(reasoning_effort=reasoning_effort, prompt=prompt_text)
    )
    raise typer.Exit(code=return_code)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
