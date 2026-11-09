import importlib
import os
import platform
import re
import shlex
from pathlib import Path
from typing import cast

import questionary
import typer
import typer.main
from questionary import Choice
from typer.core import TyperArgument, TyperOption
from typer.models import TyperPath

from stackops.scripts.python.graph.visualize.cli_graph_app import RunActionLoose
from stackops.scripts.python.graph.visualize.cli_graph_search import CliGraphSearchEntry, matching_entries, pick_entry
from stackops.utils.cli_utils.interaction import require_interactive
from stackops.utils.code import exit_then_run_shell_script


PREFILLED_PROMPT_NOTICE = "📝 Command built but NOT run yet. It is typed into your prompt below: edit it if needed, then press Enter to run it (Ctrl-C discards it)."


def run_cli_graph(graph_path: Path, query: str, action: RunActionLoose, skip_prompts: bool) -> int:
    require_interactive("""Picking a command to run""")
    handoff_path: Path | None = None
    if action in ("type", "t"):
        op_program_path_raw = os.environ.get("OP_PROGRAM_PATH")
        if op_program_path_raw is None or Path(op_program_path_raw).exists():
            raise ValueError(
                """--action type pre-types the command in your shell prompt, which needs the StackOps shell wrapper. Run it through the `devops` alias (e.g. `devops self explore run`), or use --action run / --action print."""
            )
        handoff_path = Path(op_program_path_raw)

    entry = pick_entry(entries=matching_entries(graph_path=graph_path, query=query), graph_path=graph_path, query=query)
    if entry is None:
        return 0
    command_line = _join_tokens(tokens=list(entry.command_tokens)) if skip_prompts else build_command_line(entry=entry)
    if command_line is None:
        return 0

    if handoff_path is not None:
        write_shell_prefill(command_line=command_line, handoff_path=handoff_path)
    elif action in ("run", "r"):
        typer.echo(f"""🚀 Running: {command_line}""")
        exit_then_run_shell_script(script=command_line, strict=False)
    else:
        print(command_line)
    return 0


def build_command_line(entry: CliGraphSearchEntry) -> str | None:
    tokens = list(entry.command_tokens)
    if entry.entry.get("kind") == "group":
        return _join_tokens(tokens=tokens)

    parameters = _load_typer_parameters(entry=entry)
    options = [parameter for parameter in parameters if isinstance(parameter, TyperOption)]
    arguments = [parameter for parameter in parameters if isinstance(parameter, TyperArgument)]

    option_tokens: dict[int, list[str]] = {}
    last_picked = "done"
    while options:
        chosen_option_tokens = [token for index in sorted(option_tokens) for token in option_tokens[index]]
        menu = [
            Choice(
                title=f"""✅ Done → {_join_tokens(tokens=[*tokens, *chosen_option_tokens])}""",
                value="done",
                description="Finish the options and continue to the arguments.",
            )
        ]
        for index, option in enumerate(options):
            set_tokens = option_tokens.get(index)
            menu.append(
                Choice(
                    title=f"""{"●" if set_tokens else "○"} {", ".join([*option.opts, *option.secondary_opts])}{" (required)" if option.required else ""}{f"  → {_join_tokens(tokens=set_tokens)}" if set_tokens else ""}""",
                    value=str(index),
                    description=" ".join((option.help or "").split()) or None,
                )
            )
        picked = cast(
            str | None,
            questionary.select(f"""Options for `{entry.command}` (Enter on an option sets or clears it):""", choices=menu, default=last_picked).ask(),
        )
        if picked is None:
            return None
        if picked == "done":
            break
        last_picked = picked
        index = int(picked)
        option = options[index]
        flag = next((opt for opt in option.opts if opt.startswith("--")), option.opts[0])
        if option.is_flag and option.secondary_opts:
            chosen_flag = cast(
                str | None,
                questionary.select(f"""Set {flag}:""", choices=[flag, option.secondary_opts[0], Choice(title="(not set)", value="")]).ask(),
            )
            if chosen_flag is None:
                return None
            new_tokens = [chosen_flag] if chosen_flag else []
        elif option.is_flag or option.count:
            new_tokens = [] if index in option_tokens else [flag]
        else:
            values = _ask_values(message=f"""{flag} (empty clears it):""", parameter=option, multiple=option.multiple)
            if values is None:
                return None
            new_tokens = [token for value in values for token in (flag, value)]
        if new_tokens:
            option_tokens[index] = new_tokens
        else:
            option_tokens.pop(index, None)
    tokens.extend(token for index in sorted(option_tokens) for token in option_tokens[index])

    for argument in arguments:
        argument_help = " ".join((getattr(argument, "help", None) or "").split())
        required_marker = " (required)" if argument.required else " (optional)"
        values = _ask_values(
            message=f"""{(argument.name or "").upper()}{required_marker}{f" — {argument_help}" if argument_help else ""}:""",
            parameter=argument,
            multiple=argument.nargs == -1,
        )
        if values is None:
            return None
        if not values:
            break
        tokens.extend(values)

    return _join_tokens(tokens=tokens)


def write_shell_prefill(command_line: str, handoff_path: Path) -> None:
    if platform.system() == "Windows":
        powershell_literal = f"""{command_line.replace("'", "''")} """
        script = f"""Write-Host "{PREFILLED_PROMPT_NOTICE}"
$null = Register-EngineEvent -SourceIdentifier PowerShell.OnIdle -MaxTriggerCount 1 -Action {{ [Microsoft.PowerShell.PSConsoleReadLine]::Insert('{powershell_literal}') }}
"""
    else:
        quoted_command_line = shlex.quote(f"""{command_line} """)
        script = f"""if [ -n "$ZSH_VERSION" ]; then
    echo "{PREFILLED_PROMPT_NOTICE}"
    print -z -- {quoted_command_line}
else
    history -s -- {quoted_command_line}
    echo "📝 Command built but NOT run yet. It is in your shell history: press ↑, edit it if needed, then press Enter to run it."
    echo {quoted_command_line}
fi
"""
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(script, encoding="utf-8")


def _load_typer_parameters(entry: CliGraphSearchEntry) -> list[TyperArgument | TyperOption]:
    source = entry.entry.get("source")
    if not isinstance(source, dict):
        raise ValueError(f"""CLI graph entry `{entry.command}` has no source to load its parameters from.""")
    source_object = cast(dict[str, object], source)
    module_name = source_object.get("module")
    callable_name = source_object.get("callable")
    if not isinstance(module_name, str) or not isinstance(callable_name, str):
        raise ValueError(f"""CLI graph entry `{entry.command}` has no module/callable source.""")
    function = getattr(importlib.import_module(module_name), callable_name, None)
    if not callable(function):
        raise ValueError(f"""Cannot load `{module_name}.{callable_name}` to guide `{entry.command}`: it is not a module-level callable.""")
    app = typer.Typer(add_completion=False)
    app.command()(function)
    return [parameter for parameter in typer.main.get_command(app).params if isinstance(parameter, TyperArgument | TyperOption)]


def _ask_values(message: str, parameter: TyperArgument | TyperOption, multiple: bool) -> list[str] | None:
    raw_choices = getattr(parameter.type, "choices", None)
    if isinstance(raw_choices, list | tuple) and raw_choices:
        choice_titles = [str(choice) for choice in cast(list[object] | tuple[object, ...], raw_choices)]
        if multiple:
            return cast(list[str] | None, questionary.checkbox(message, choices=choice_titles).ask())
        selected = cast(str | None, questionary.select(message, choices=[*choice_titles, Choice(title="(leave empty)", value="")]).ask())
        return None if selected is None else [selected] if selected else []
    if isinstance(parameter.type, TyperPath):
        answer = cast(str | None, questionary.path(message).ask())
    else:
        answer = cast(str | None, questionary.text(message).ask())
    if answer is None:
        return None
    if multiple:
        return shlex.split(answer)
    return [answer] if answer.strip() else []


def _join_tokens(tokens: list[str]) -> str:
    if platform.system() == "Windows":
        return " ".join(token if re.fullmatch(r"[\w@%+=:,./\\-]+", token) else f"""'{token.replace("'", "''")}'""" for token in tokens)
    return shlex.join(tokens)
