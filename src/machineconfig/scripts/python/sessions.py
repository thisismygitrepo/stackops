"""Sessions management commands - lazy loading subcommands."""

from typing import Literal, Annotated
import typer


def _resolve_session_backend(
    backend: Literal["zellij", "z", "tmux", "t", "auto", "a"],
) -> Literal["zellij", "tmux"]:
    import platform

    system = platform.system().lower()
    match backend:
        case "zellij" | "z":
            if system == "windows":
                typer.echo("Error: Zellij is not supported on Windows.", err=True, color=True)
                raise typer.Exit()
            return "zellij"
        case "tmux" | "t":
            if system == "windows":
                typer.echo("Error: tmux is not supported on Windows.", err=True, color=True)
                raise typer.Exit()
            return "tmux"
        case "auto" | "a":
            if system == "windows":
                typer.echo("Error: tmux/zellij are not supported on Windows.", err=True, color=True)
                raise typer.Exit()
            return "zellij"
        case _:
            typer.echo(f"Error: Unsupported backend '{backend}'.", err=True, color=True)
            raise typer.Exit()


def balance_load(
    layout_path: Annotated[str, typer.Argument(..., help="Path to the layout.json file")],
    max_thresh: Annotated[int, typer.Option(..., "--max-threshold", "-m", help="Maximum tabs per layout")],
    thresh_type: Annotated[Literal["number", "n", "weight", "w"], typer.Option(..., "--threshold-type", "-t", help="Threshold type")] = "number",
    breaking_method: Annotated[Literal["moreLayouts", "ml", "combineTabs", "ct"], typer.Option(..., "--breaking-method", "-b", help="Breaking method")] = "moreLayouts",
    output_path: Annotated[str | None, typer.Option(..., "--output-path", "-o", help="Path to write the adjusted layout.json file")] = None,
) -> None:
    """Adjust layout file to limit max tabs per layout, etc."""
    from machineconfig.scripts.python.helpers.helpers_sessions.utils import balance_load as impl
    impl(layout_path=layout_path, max_thresh=max_thresh, thresh_type=thresh_type, breaking_method=breaking_method, output_path=output_path)


def run(
    ctx: typer.Context,
    layouts_file: Annotated[str | None, typer.Option(..., "--layouts-file", "-f", help="Path to the layout.json file")] = None,
    choose_layouts: Annotated[str | None, typer.Option(..., "--choose-layouts", "-c", help="Comma separated layout names. Pass empty string to select layouts interactively.")] = None,
    choose_tabs: Annotated[str | None, typer.Option(..., "--choose-tabs", "-t", help="Comma separated tab names. Pass empty string to select tabs interactively from all layouts.")] = None,
    sleep_inbetween: Annotated[float, typer.Option(..., "--sleep-inbetween", "-S", help="Sleep time in seconds between launching layouts")] = 1.0,

    parallel_layouts: Annotated[int | None, typer.Option(..., "--parallel-layouts", "-p", help="Maximum number of layouts to launch per monitored batch. 1 behaves like sequential mode.")] = None,
    max_tabs: Annotated[int, typer.Option(..., "--max-tabs-per-layout", "-T", help="A Sanity checker that throws an error if any layout exceeds the maximum number of tabs to launch.")] = 25,

    max_layouts: Annotated[int, typer.Option(..., "--max-parallel-layouts", "-P", help="A Sanity checker that throws an error if the total number of *parallel layouts exceeds this number.")] = 25,
    backend: Annotated[Literal["zellij", "z", "windows-terminal", "wt", "tmux", "t", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend terminal multiplexer or emulator to use")] = "tmux",
    on_conflict: Annotated[Literal["restart", "error", "rename"], typer.Option("--on-conflict", "-o", help="How to handle existing session name conflicts.")] = "error",
    max_parallel_tabs: Annotated[int | None, typer.Option("--max-parallel-tabs", help="Enable dynamic tab scheduling and cap active tabs to this value.")] = None,
    poll_seconds: Annotated[float, typer.Option("--poll-seconds", help="Dynamic mode only: polling interval in seconds used to detect finished tabs.")] = 2.0,

    kill_finished_tabs: Annotated[bool, typer.Option("--kill-finished-tabs", help="Dynamic mode only: close each tab once its command is finished.")] = False,
    all_file: Annotated[bool, typer.Option("--all-file", help="Dynamic mode only: merge tabs from all layouts in the file into one dynamic run.")] = False,
    monitor: Annotated[bool, typer.Option(..., "--monitor", "-m", help="Monitor the layout sessions for completion (implied by --parallel-layouts)")] = False,
    kill_upon_completion: Annotated[bool, typer.Option(..., "--kill-upon-completion", "-k", help="Kill session(s) upon completion (only relevant if --monitor or --parallel-layouts is set)")] = False,
    subsitute_home: Annotated[bool, typer.Option(..., "--substitute-home", "-H", help="Substitute ~ and $HOME in layout file with actual home directory path")] = False,

) -> None:
    """Launch terminal sessions based on a layout configuration file.

    Use --on-conflict to choose behavior when a target session already exists:
    error, restart, or rename.
    Pass --max-parallel-tabs to enable dynamic tab scheduling.
    """
    from machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run import run_cli as impl
    impl(
        ctx=ctx,
        layouts_file=layouts_file,
        choose_layouts=choose_layouts,
        choose_tabs=choose_tabs,
        sleep_inbetween=sleep_inbetween,
        parallel_layouts=parallel_layouts,
        max_tabs=max_tabs,
        max_layouts=max_layouts,
        backend=backend,
        on_conflict=on_conflict,
        max_parallel_tabs=max_parallel_tabs,
        poll_seconds=poll_seconds,
        kill_finished_tabs=kill_finished_tabs,
        all_file=all_file,
        monitor=monitor,
        kill_upon_completion=kill_upon_completion,
        subsitute_home=subsitute_home,
    )


def attach_to_session(
        name: Annotated[str | None, typer.Argument(help="Name of the session to attach to. If not provided, a list will be shown to choose from.")] = None,
        new_session: Annotated[bool, typer.Option("--new-session", "-n", help="Create a new session instead of attaching to an existing one.", show_default=True)] = False,
        kill_all: Annotated[bool, typer.Option("--kill-all", "-k", help="Kill all existing sessions before creating a new one.", show_default=True)] = False,
        window: Annotated[bool, typer.Option("--window", "-w", help="Choose a window/tab or pane target instead of only choosing from sessions.", show_default=True)] = False,
        backend: Annotated[Literal["zellij", "z", "tmux", "t", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend multiplexer to use")] = "tmux",
        ) -> None:
    """Choose a session or deeper target to attach to."""
    backend_resolved = _resolve_session_backend(backend)
    from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import choose_session as impl
    action, payload = impl(backend=backend_resolved, name=name, new_session=new_session, kill_all=kill_all, window=window)
    if action == "error":
        typer.echo(payload, err=True, color=True)
        raise typer.Exit()
    if action == "run_script" and payload:
        from machineconfig.utils.code import exit_then_run_shell_script
        exit_then_run_shell_script(script= payload, strict=True)


def kill_session_target(
        name: Annotated[str | None, typer.Argument(help="Name of the session to kill. If not provided, a list will be shown to choose from.")] = None,
        kill_all: Annotated[bool, typer.Option("--all", "-a", help="Kill all sessions.", show_default=True)] = False,
        window: Annotated[bool, typer.Option("--window", "-w", help="Include session, window/tab, and pane targets in the interactive chooser.", show_default=True)] = False,
        backend: Annotated[Literal["zellij", "z", "tmux", "t", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend multiplexer to use")] = "tmux",
        ) -> None:
    """Choose one or more session targets to kill."""
    if kill_all and name is not None:
        typer.echo("Error: --all cannot be used together with NAME.", err=True, color=True)
        raise typer.Exit()
    if kill_all and window:
        typer.echo("Error: --all cannot be used together with --window.", err=True, color=True)
        raise typer.Exit()
    backend_resolved = _resolve_session_backend(backend)
    from machineconfig.scripts.python.helpers.helpers_sessions.kill_impl import choose_kill_target as impl

    action, payload = impl(backend=backend_resolved, name=name, kill_all=kill_all, window=window)
    if action == "error":
        typer.echo(payload, err=True, color=True)
        raise typer.Exit()
    if action == "run_script" and payload:
        from machineconfig.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script=payload, strict=True)



def get_session_tabs() -> list[tuple[str, str]]:
    """Get all Zellij session tabs."""
    from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import get_session_tabs as impl
    result = impl()
    print(result)
    return result
def create_template(
    name: Annotated[str | None, typer.Argument(..., help="Name of the layout template to create")] = None,
    num_tabs: Annotated[int, typer.Option(..., "--num-tabs", "-t", help="Number of tabs to include in the template")] = 3,
) -> None:
    """Create a layout template file."""
    from machineconfig.scripts.python.helpers.helpers_sessions.utils import create_template as impl
    impl(name=name, num_tabs=num_tabs)

def create_from_function(
    num_process: Annotated[int, typer.Option(..., "--num-process", "-n", help="Number of parallel processes to run")],
    path: Annotated[str, typer.Option(..., "--path", "-p", help="Path to a Python or Shell script file or a directory containing such files")] = ".",
    function: Annotated[str | None, typer.Option(..., "--function", "-f", help="Function to run from the Python file. If not provided, you will be prompted to choose.")] = None,
) -> None:
    """Create a layout from a function to run in multiple processes."""
    from machineconfig.scripts.python.helpers.helpers_sessions.sessions_multiprocess import create_from_function as impl
    impl(num_process=num_process, path=path, function=function)


def summarize(
    layout_path: Annotated[str, typer.Argument(..., help="Path to the layout.json file")],
) -> None:
    """Summarize a layout file with counts for layouts and tabs."""
    import json
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from machineconfig.utils.io import remove_c_style_comments

    console = Console()
    layout_path_obj = Path(layout_path).expanduser().absolute()

    if not layout_path_obj.exists():
        console.print(
            Panel(
                f"❌ Layout file not found:\n{layout_path_obj}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    json_str = layout_path_obj.read_text(encoding="utf-8")
    try:
        layout_file = json.loads(json_str)
    except Exception:
        try:
            layout_file = json.loads(remove_c_style_comments(json_str))
        except Exception as e:
            console.print(
                Panel(
                    f"❌ Failed to parse JSON file:\n{layout_path_obj}\n\n{e}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from e

    if not isinstance(layout_file, dict):
        console.print(Panel("❌ Layout file root must be a JSON object.", title="Error", border_style="red"))
        raise typer.Exit(code=1)

    layouts_raw = layout_file.get("layouts")
    if not isinstance(layouts_raw, list):
        console.print(Panel("❌ Missing or invalid 'layouts' array.", title="Error", border_style="red"))
        raise typer.Exit(code=1)

    rows: list[tuple[int, str, int]] = []
    total_tabs = 0
    for index, a_layout in enumerate(layouts_raw, start=1):
        if isinstance(a_layout, dict):
            layout_name = str(a_layout.get("layoutName", f"layout#{index}"))
            layout_tabs = a_layout.get("layoutTabs")
            tab_count = len(layout_tabs) if isinstance(layout_tabs, list) else 0
        else:
            layout_name = f"invalid-layout#{index}"
            tab_count = 0
        rows.append((index, layout_name, tab_count))
        total_tabs += tab_count

    total_layouts = len(rows)
    avg_tabs = (total_tabs / total_layouts) if total_layouts > 0 else 0.0
    version = str(layout_file.get("version", "unknown"))

    summary_lines = [
        f"[bold]File:[/bold] {layout_path_obj}",
        f"[bold]Version:[/bold] {version}",
        f"[bold]Layouts:[/bold] {total_layouts}",
        f"[bold]Tabs:[/bold] {total_tabs}",
        f"[bold]Avg tabs/layout:[/bold] {avg_tabs:.2f}",
    ]
    if rows:
        max_row = max(rows, key=lambda row: row[2])
        min_row = min(rows, key=lambda row: row[2])
        summary_lines.append(f"[bold]Max tabs layout:[/bold] {max_row[1]} ({max_row[2]})")
        summary_lines.append(f"[bold]Min tabs layout:[/bold] {min_row[1]} ({min_row[2]})")

    console.print(Panel("\n".join(summary_lines), title="[bold blue]Layout Summary[/bold blue]", border_style="blue"))

    table = Table(title=f"[bold cyan]Layouts ({total_layouts})[/bold cyan]")
    table.add_column("#", justify="right")
    table.add_column("Layout Name", style="white")
    table.add_column("Tabs", justify="right", style="green")
    for index, layout_name, tab_count in rows:
        table.add_row(str(index), layout_name, str(tab_count))
    console.print(table)


def trace(
    session_name: Annotated[str, typer.Argument(..., help="Name of the tmux session to trace")],
    every: Annotated[float, typer.Option("--every", "-e", help="Polling interval in seconds between tmux checks")] = 10.0,
    until: Annotated[Literal["idle-shell", "all-exited", "exit-code", "session-missing"], typer.Option("--until", "-u", help="Stop only when the selected criterion is satisfied")] = "idle-shell",
    exit_code: Annotated[int | None, typer.Option("--exit-code", help="Required pane exit code when `--until exit-code` is selected")] = None,
) -> None:
    """Trace a tmux session until every target matches a strict stop criterion."""
    from machineconfig.scripts.python.helpers.helpers_sessions.sessions_trace import trace_session as impl

    impl(
        session_name=session_name,
        until=until,
        every_seconds=every,
        exit_code=exit_code,
    )


def run_aoe(
    ctx: typer.Context,
    layouts_file: Annotated[str | None, typer.Option(..., "--layouts-file", "-f", help="Path to the layout.json file")] = None,
    choose_layouts: Annotated[str | None, typer.Option(..., "--choose-layouts", "-c", help="Comma separated layout names. Pass empty string to select layouts interactively.")] = None,
    choose_tabs: Annotated[str | None, typer.Option(..., "--choose-tabs", "-t", help="Comma separated tab names. Pass empty string to select tabs interactively from all layouts.")] = None,
    sleep_inbetween: Annotated[float, typer.Option(..., "--sleep-inbetween", "-S", help="Sleep time in seconds between AoE session launches")] = 1.0,
    max_tabs: Annotated[int, typer.Option(..., "--max-tabs-per-layout", "-T", help="A sanity checker that throws an error if any selected layout exceeds this number of tabs.")] = 25,
    agent: Annotated[str | None, typer.Option("--agent", help="AoE tool/agent name. Defaults to codex so --model/--sandbox/--yolo are immediately useful.")] = "codex",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model forwarded to the underlying AoE/agent CLI when supported.")] = None,
    provider: Annotated[str | None, typer.Option("--provider", "-p", help="Provider forwarded to the underlying AoE/agent CLI when supported.")] = None,
    sandbox: Annotated[str | None, typer.Option("--sandbox", help="Convenience flag forwarded to the launched agent CLI as `--sandbox <value>` when supported.")] = None,
    yolo: Annotated[bool, typer.Option("--yolo", help="Enable AoE/agent YOLO mode when supported.")] = False,
    cmd: Annotated[str | None, typer.Option("--cmd", help="Override the launched agent binary/command.")] = None,
    args: Annotated[list[str] | None, typer.Option("--args", help="Repeatable extra argument forwarded to the launched agent CLI.")] = None,
    env: Annotated[list[str] | None, typer.Option("--env", help="Repeatable KEY=VALUE pair forwarded to AoE when supported.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Pass force/overwrite to AoE when supported.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print generated `aoe add` commands instead of executing them.")] = False,
    aoe_bin: Annotated[str, typer.Option("--aoe-bin", help="AoE executable to invoke.")] = "aoe",
    tab_command_mode: Annotated[Literal["prompt", "cmd", "ignore"], typer.Option("--tab-command-mode", help="How to use each tab's `command` field: as the initial prompt, as an agent-command override, or ignore it.")] = "prompt",
    subsitute_home: Annotated[bool, typer.Option(..., "--substitute-home", "-H", help="Substitute ~ and $HOME in layout file with actual home directory path")] = False,
    launch: Annotated[bool, typer.Option("--launch/--no-launch", help="Launch each AoE session immediately after creating it.")] = True,
) -> None:
    """Launch selected layout tabs as agent-of-empires sessions.

    Mapping:
    - layoutName -> aoe --group
    - tabName -> aoe --title
    - startDir -> aoe add <path>
    - command -> initial prompt by default
    """
    from machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_run_aoe import run_aoe_cli as impl
    impl(
        ctx=ctx,
        layouts_file=layouts_file,
        choose_layouts=choose_layouts,
        choose_tabs=choose_tabs,
        sleep_inbetween=sleep_inbetween,
        max_tabs=max_tabs,
        agent=agent,
        model=model,
        provider=provider,
        sandbox=sandbox,
        yolo=yolo,
        cmd=cmd,
        args=args or [],
        env=env or [],
        force=force,
        dry_run=dry_run,
        aoe_bin=aoe_bin,
        tab_command_mode=tab_command_mode,
        subsitute_home=subsitute_home,
        launch=launch,
    )


def get_app() -> typer.Typer:
    layouts_app = typer.Typer(help="Layouts management subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)

    layouts_app.command("run", no_args_is_help=True, help=run.__doc__, short_help="<r> Run the selected layout(s)")(run)
    layouts_app.command("r", no_args_is_help=True, help=run.__doc__, hidden=True)(run)
    
    layouts_app.command("run-aoe", no_args_is_help=True, help=run_aoe.__doc__, short_help="<e> Run selected layout(s) through agent-of-empires")(run_aoe)
    layouts_app.command("e", no_args_is_help=True, help=run_aoe.__doc__, hidden=True)(run_aoe)

    layouts_app.command("attach", no_args_is_help=False, help=attach_to_session.__doc__, short_help="<a> Attach to a session target")(attach_to_session)
    layouts_app.command("a", no_args_is_help=False, help=attach_to_session.__doc__, hidden=True)(attach_to_session)

    layouts_app.command("kill", no_args_is_help=False, help=kill_session_target.__doc__, short_help="<k> Kill a session target")(kill_session_target)
    layouts_app.command("k", no_args_is_help=False, help=kill_session_target.__doc__, hidden=True)(kill_session_target)

    layouts_app.command("trace", no_args_is_help=True, help=trace.__doc__, short_help="<x> Trace a tmux session until it settles")(trace)
    layouts_app.command("x", no_args_is_help=True, help=trace.__doc__, hidden=True)(trace)

    layouts_app.command("create-from-function", no_args_is_help=True, short_help="<c> Create a layout from a function")(create_from_function)
    layouts_app.command("c", no_args_is_help=True, hidden=True)(create_from_function)

    layouts_app.command("balance-load", no_args_is_help=True, help=balance_load.__doc__, short_help="<b> Balance the load across sessions")(balance_load)
    layouts_app.command("b", no_args_is_help=True, help=balance_load.__doc__, hidden=True)(balance_load)

    layouts_app.command("create-template", no_args_is_help=False, help=create_template.__doc__, short_help="<p> Create a layout template file")(create_template)
    layouts_app.command("p", no_args_is_help=False, help=create_template.__doc__, hidden=True)(create_template)

    layouts_app.command("summarize", no_args_is_help=True, help=summarize.__doc__, short_help="<s> Summarize a layout file")(summarize)
    layouts_app.command("s", no_args_is_help=True, help=summarize.__doc__, hidden=True)(summarize)
    return layouts_app


def main() -> None:
    layouts_app = get_app()
    layouts_app()


if __name__ == "__main__":
    main()
