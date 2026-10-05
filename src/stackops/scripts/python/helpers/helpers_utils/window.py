import subprocess
import sys
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_window.window_models import WindowAction


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
) -> None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    if list_windows and action is not None:
        raise typer.BadParameter("--list cannot be combined with --action.")
    if title is not None and not title.strip():
        raise typer.BadParameter("--title must not be blank.")

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
        if not windows:
            typer.echo("No matching windows found." if title is not None else "No open windows found.")
            return

        labels = {
            f"""{index}. {' '.join(entry.app.split())} — {' '.join(entry.title.split()) or '(untitled)'}{' [minimized]' if entry.minimized else ''}""": entry
            for index, entry in enumerate(windows, start=1)
        }
        if list_windows:
            typer.echo("\n".join(labels))
            return

        if title is not None and len(windows) == 1:
            selected_window = windows[0]
        else:
            if not sys.stdin.isatty():
                raise RuntimeError("Window selection requires an interactive terminal. Use --title to match one window.")
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
                return
            selected_window = labels[selected_label]

        if action is None:
            from stackops.scripts.python.helpers.helpers_window.constants import ACTION_DESCRIPTIONS

            if not sys.stdin.isatty():
                raise RuntimeError("Action selection requires an interactive terminal. Pass --action.")
            typer.echo(f"""Select an action for {selected_window.app} — {selected_window.title or '(untitled)'}:""")
            action_previews: dict[str, str] = {candidate: description for candidate, description in ACTION_DESCRIPTIONS.items()}
            selected_action = choose_from_dict_with_preview(
                options_to_preview_mapping=action_previews,
                extension="txt",
                multi=False,
                preview_size_percent=50.0,
            )
            if selected_action is None:
                return
            action = next(candidate for candidate in ACTION_DESCRIPTIONS if candidate == selected_action)

        selected_window.apply_action(action)
        typer.echo(f"""{action}: {selected_window.app} — {selected_window.title or '(untitled)'}""")
    except FileNotFoundError as error:
        typer.echo("Error: interactive window selection requires Television (tv) on PATH.", err=True)
        raise typer.Exit(code=1) from error
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error
