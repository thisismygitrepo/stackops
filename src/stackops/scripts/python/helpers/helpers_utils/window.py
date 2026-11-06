import json
import subprocess
import sys
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_window.window_models import WindowAction
from stackops.utils.cli_utils.interaction import require_interactive


def window(
    action: Annotated[
        WindowAction | None,
        typer.Option("--action", "-a", help="Action to perform; choose interactively when omitted."),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Match window titles (case insensitive); select directly when exactly one matches."),
    ] = None,
    list_windows: Annotated[
        bool,
        typer.Option("--list", "-l", help="List open windows, including minimized windows, and exit."),
    ] = False,
    window_id: Annotated[str | None, typer.Option("--id", "-I", help="Exact window identifier from --list --json; valid while that window remains open.")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print the window list or action receipt as JSON; never prompts.")] = False,
) -> None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    if list_windows and action is not None:
        raise typer.BadParameter("--list cannot be combined with --action.")
    if title is not None and not title.strip():
        raise typer.BadParameter("--title must not be blank.")
    if window_id is not None and title is not None:
        raise typer.BadParameter("Choose --id or --title, not both.")
    if window_id is not None and not window_id.strip():
        raise typer.BadParameter("--id must not be blank.")
    if not list_windows and action is None:
        if json_output:
            raise typer.BadParameter("JSON actions require --action and --id or a unique --title.")
        require_interactive("Choose a window action; supply --action")
    if not list_windows and window_id is None and title is None:
        if json_output:
            raise typer.BadParameter("JSON actions require --id or a unique --title.")
        require_interactive("Choose a window; use --list --json then --id ID --action ACTION")

    try:
        if sys.platform == "darwin":
            from stackops.scripts.python.helpers.helpers_window.window_macos import collect_windows
        elif sys.platform == "linux":
            from stackops.scripts.python.helpers.helpers_window.window_linux import collect_windows
        elif sys.platform == "win32":
            from stackops.scripts.python.helpers.helpers_window.window_windows import collect_windows
        else:
            raise RuntimeError(f"""Window management is not supported on {sys.platform}.""")

        windows = collect_windows()
        if title is not None:
            windows = [entry for entry in windows if title.casefold() in entry.title.casefold()]
        if window_id is not None:
            windows = [entry for entry in windows if window_id == entry.id]
        if list_windows and json_output:
            typer.echo(json.dumps({"windows": [{"id": entry.id, "app": entry.app, "title": entry.title, "minimized": entry.minimized} for entry in windows]}, indent=2))
            return
        if not windows:
            if not list_windows:
                raise RuntimeError("No matching open window found; refresh --list --json before retrying.")
            typer.echo("No matching windows found." if title is not None else "No open windows found.")
            return

        labels = {
            f"""{entry.id} {' '.join(entry.app.split())} — {' '.join(entry.title.split()) or '(untitled)'}{' [minimized]' if entry.minimized else ''}""": entry
            for entry in windows
        }
        if list_windows:
            typer.echo("\n".join(labels))
            return

        if (window_id is not None or title is not None) and len(windows) == 1:
            selected_window = windows[0]
        else:
            if json_output:
                raise typer.BadParameter("The title is ambiguous; select an exact --id from --list --json.")
            require_interactive("Choose among matching windows; use --list --json then --id ID")
            typer.echo("Select a window:")
            selected_label = choose_from_dict_with_preview(
                options_to_preview_mapping={
                    label: f"""Application: {entry.app}
Title: {entry.title or '(untitled)'}
Minimized: {entry.minimized}"""
                    for label, entry in labels.items()
                },
                extension="txt",
                multi=False,
                preview_size_percent=50.0,
            )
            if selected_label is None:
                raise typer.Exit(code=1)
            selected_window = labels[selected_label]

        resolved_action: WindowAction
        if action is None:
            from stackops.scripts.python.helpers.helpers_window.constants import ACTION_DESCRIPTIONS

            require_interactive("Choose a window action; supply --action")
            typer.echo(f"""Select an action for {selected_window.app} — {selected_window.title or '(untitled)'}:""")
            action_previews: dict[str, str] = {candidate: description for candidate, description in ACTION_DESCRIPTIONS.items()}
            selected_action = choose_from_dict_with_preview(
                options_to_preview_mapping=action_previews,
                extension="txt",
                multi=False,
                preview_size_percent=50.0,
            )
            if selected_action is None:
                raise typer.Exit(code=1)
            resolved_action = next(candidate for candidate in ACTION_DESCRIPTIONS if candidate == selected_action)
        else:
            resolved_action = action

        selected_window.apply_action(resolved_action)
        if json_output:
            typer.echo(json.dumps({"status": "completed", "id": selected_window.id, "action": resolved_action, "app": selected_window.app, "title": selected_window.title}))
        else:
            typer.echo(f"""{resolved_action}: {selected_window.app} — {selected_window.title or '(untitled)'}""")
    except FileNotFoundError as error:
        typer.echo("Error: interactive window selection requires Television (tv) on PATH.", err=True)
        raise typer.Exit(code=1) from error
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error
