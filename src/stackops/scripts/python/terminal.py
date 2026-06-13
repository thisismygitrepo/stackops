"""Terminal management commands - lazy loading subcommands."""

from typing import Literal, Annotated
import typer

_SessionConflictActionLoose = Literal[
    "restart", "r",
    "rename", "n",
    "error", "e",
    "skip", "s",
    "mergeOverwrite", "m",
    "mergeSkip", "M",
]


def balance_load(
    layout_path: Annotated[str, typer.Argument(..., help="Path to the layout.json file")],
    max_thresh: Annotated[int, typer.Option(..., "--max-threshold", "-m", help="Maximum tabs per layout")],
    thresh_type: Annotated[Literal["number", "n", "weight", "w"], typer.Option(..., "--threshold-type", "-t", help="Threshold type")] = "number",
    breaking_method: Annotated[Literal["moreLayouts", "ml", "combineTabs", "ct"], typer.Option(..., "--breaking-method", "-b", help="Breaking method")] = "moreLayouts",
    output_path: Annotated[str | None, typer.Option(..., "--output-path", "-o", help="Path to write the adjusted layout.json file")] = None,
) -> None:
    """Adjust layout file to limit max tabs per layout, etc."""
    from stackops.scripts.python.helpers.helpers_sessions.utils import balance_load as impl
    try:
        impl(layout_path=layout_path, max_thresh=max_thresh, thresh_type=thresh_type, breaking_method=breaking_method, output_path=output_path)
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True, color=True)
        raise typer.Exit(code=1) from error


def run(
    ctx: typer.Context,
    layouts_file: Annotated[str | None, typer.Option(..., "--layouts-file", "-f", help="Path to the layout.json file")] = None,
    test_layout: Annotated[bool, typer.Option(..., "--test-layout", "-L", help="Generate a built-in mock layout with many finite tabs for experimenting with run and run-all. Cannot be used with --layouts-file.")] = False,

    choose_layouts: Annotated[str | None, typer.Option(..., "--choose-layouts", "-l", help="Comma separated layout names. Pass empty string to select layouts interactively.")] = None,
    choose_tabs: Annotated[str | None, typer.Option(..., "--choose-tabs", "-t", help="Comma separated tab names. Pass empty string to select tabs interactively from all layouts.")] = None,
    sleep_inbetween: Annotated[float, typer.Option(..., "--sleep-inbetween", "-S", help="Sleep time in seconds between launching layouts")] = 1.0,
    max_tabs: Annotated[int, typer.Option(..., "--max-tabs-per-layout", "-T", help="A Sanity checker that throws an error if any layout exceeds the maximum number of tabs to launch.")] = 25,
    max_layouts: Annotated[int, typer.Option(..., "--max-parallel-layouts", "-P", help="A Sanity checker that throws an error if the total number of *parallel layouts exceeds this number.")] = 25,
    monitor: Annotated[bool, typer.Option(..., "--monitor", "-m", help="Monitor the layout sessions for completion (implied by --parallel-layouts)")] = False,
    parallel_layouts: Annotated[int | None, typer.Option(..., "--parallel-layouts", "-p", help="Maximum number of layouts to launch per monitored batch. 1 behaves like sequential mode.")] = None,

    backend: Annotated[Literal["windows-terminal", "wt", "tmux", "t", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend terminal multiplexer or emulator to use")] = "tmux",
    on_conflict: Annotated[_SessionConflictActionLoose, typer.Option("--on-conflict", "-c", help="How to handle existing session name conflicts. mergeOverwrite and mergeSkip are supported for tmux and Windows Terminal.")] = "error",
    exit_mode: Annotated[Literal["backToShell", "terminate", "killWindow"], typer.Option("--exit", "-e", help="What each tab/window should do after its command exits.")] = "backToShell",
    kill_upon_completion: Annotated[bool, typer.Option(..., "--kill-upon-completion", "-k", help="Kill session(s) upon completion (only relevant if --monitor or --parallel-layouts is set)")] = False,
    subsitute_home: Annotated[bool, typer.Option(..., "--substitute-home", "-H", help="Substitute ~ and $HOME in layout file with actual home directory path")] = False,

) -> None:
    """Launch selected layouts from a layout configuration file.

    Use --on-conflict to choose behavior when a target session already exists:
    error, restart, rename, mergeOverwrite, or
    mergeSkip. Those two merge policies are
    supported for tmux and Windows Terminal.
    Use `run-all` for the paced whole-file dynamic scheduler.

    The type of parallelization here is constrained by layouts. It asumes that every layout is a self-contained unit that must be launched in its entirety before the next one is launched, but multiple layouts can be launched at the same time if --parallel-layouts is set. If you want to launch every tab as soon as possible without waiting for the whole layout to launch, use `run-all` instead.
    """
    from stackops.cluster.sessions_managers.session_conflict import SessionConflictActionLoose2Strict
    on_conflict = SessionConflictActionLoose2Strict[on_conflict]
    from stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run import run_cli as impl
    impl(
        ctx=ctx,
        layouts_file=layouts_file,
        test_layout=test_layout,
        choose_layouts=choose_layouts,
        choose_tabs=choose_tabs,
        sleep_inbetween=sleep_inbetween,
        parallel_layouts=parallel_layouts,
        max_tabs=max_tabs,
        max_layouts=max_layouts,
        backend=backend,
        on_conflict=on_conflict,
        exit_mode=exit_mode,
        monitor=monitor,
        kill_upon_completion=kill_upon_completion,
        subsitute_home=subsitute_home,
    )


def run_all(
    ctx: typer.Context,
    *,
    layouts_file: Annotated[str | None, typer.Option(..., "--layouts-file", "-f", help="Path to the layout.json file")] = None,
    test_layout: Annotated[bool, typer.Option(..., "--test-layout", "-T", help="Generate a built-in mock layout with many finite tabs for experimenting with run and run-all. Cannot be used with --layouts-file.")] = False,
    max_parallel_tabs: Annotated[int, typer.Option(..., "--max-parallel-tabs", "-t", help="Maximum number of tabs to keep active while dynamically working through the whole file.")],
    poll_seconds: Annotated[float, typer.Option("--poll-seconds", "-p", help="Polling interval in seconds used to detect finished tabs.")] = 2.0,
    kill_finished_tabs: Annotated[bool, typer.Option("--kill-finished-tabs", "-k", help="Close each tab once its command is finished.")] = False,
    backend: Annotated[Literal["tmux", "t", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend terminal multiplexer to use")] = "tmux",
    on_conflict: Annotated[_SessionConflictActionLoose, typer.Option("--on-conflict", "-c", help="How to handle existing session name conflicts. run-all only supports error, restart, and rename because the dynamic scheduler must own the target session.")] = "error",
    subsitute_home: Annotated[bool, typer.Option(..., "--substitute-home", "-H", help="Substitute ~ and $HOME in layout file with actual home directory path")] = False,
) -> None:
    """Run every tab from every layout in a layout configuration file at a controlled pace.
    New tab kicks in as soon as another tab finishes, keeping the total number of active tabs under the specified maximum.
    Use this if problem is embarresingly parallel and is only constrained by resources.
    """
    if max_parallel_tabs < 1:
        typer.echo("Error: --max-parallel-tabs must be at least 1.", err=True, color=True)
        raise typer.Exit(code=1)
    if poll_seconds <= 0.0:
        typer.echo("Error: --poll-seconds must be greater than 0.", err=True, color=True)
        raise typer.Exit(code=1)

    from stackops.cluster.sessions_managers.session_conflict import SessionConflictActionLoose2Strict
    on_conflict = SessionConflictActionLoose2Strict[on_conflict]
    if on_conflict in {"mergeOverwrite", "mergeSkip"}:
        typer.echo(
            "Error: --on-conflict mergeOverwrite and mergeSkip are not supported for run-all because the dynamic scheduler requires exclusive control of the session.",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    from stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_all import run_all_cli as impl
    impl(
        ctx=ctx,
        layouts_file=layouts_file,
        test_layout=test_layout,
        max_parallel_tabs=max_parallel_tabs,
        poll_seconds=poll_seconds,
        kill_finished_tabs=kill_finished_tabs,
        backend=backend,
        on_conflict=on_conflict,
        subsitute_home=subsitute_home,
    )


def attach_to_session(
        name: Annotated[str | None, typer.Argument(help="Name of the session to attach to. If not provided, a list will be shown to choose from.")] = None,
        new_session: Annotated[bool, typer.Option("--new-session", "-n", help="Create a new session instead of attaching to an existing one.", show_default=True)] = False,
        kill_all: Annotated[bool, typer.Option("--kill-all", "-k", help="Kill all existing sessions before creating a new one.", show_default=True)] = False,
        window: Annotated[bool, typer.Option("--window", "-w", help="Choose a window/tab or pane target instead of only choosing from sessions.", show_default=True)] = False,
        backend: Annotated[Literal["tmux", "t", "herdr", "h", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend multiplexer to use")] = "tmux",
        ) -> None:
    """Choose a session or deeper target to attach to."""
    if name is not None and new_session:
        typer.echo("Error: NAME cannot be used together with --new-session.", err=True, color=True)
        raise typer.Exit(code=1)
    if name is not None and kill_all:
        typer.echo("Error: NAME cannot be used together with --kill-all.", err=True, color=True)
        raise typer.Exit(code=1)
    if name is not None and window:
        typer.echo("Error: NAME cannot be used together with --window.", err=True, color=True)
        raise typer.Exit(code=1)
    from stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers import resolve_session_backend
    backend_resolved = resolve_session_backend(backend)
    from stackops.scripts.python.helpers.helpers_sessions.attach_impl import choose_session as impl
    action, payload = impl(backend=backend_resolved, name=name, new_session=new_session, kill_all=kill_all, window=window)
    if action == "error":
        typer.echo(payload, err=True, color=True)
        raise typer.Exit(code=1)
    if action == "handoff_script":
        from stackops.utils.code import exit_then_run_shell_script

        if payload.strip() == "":
            typer.echo("Error: attach operation did not return a final handoff script.", err=True, color=True)
            raise typer.Exit(code=1)
        exit_then_run_shell_script(script=payload, strict=True)
        return
    typer.echo("Error: attach operation did not return a final handoff script.", err=True, color=True)
    raise typer.Exit(code=1)


def kill_session_target(
        name: Annotated[str | None, typer.Argument(help="Name of the session to kill. If not provided, a list will be shown to choose from.")] = None,
        kill_all: Annotated[bool, typer.Option("--all", "-a", help="Kill all sessions. With --idle, inspect all sessions for idle panes/windows.", show_default=True)] = False,
        idle: Annotated[bool, typer.Option("--idle", "-i", help="Kill idle-shell panes/windows. With --all, inspect all sessions; otherwise inspect NAME or a chosen session.", show_default=True)] = False,
        window: Annotated[bool, typer.Option("--window", "-w", help="Include session, window/tab, and pane targets in the interactive chooser when NAME is omitted.", show_default=True)] = False,
        backend: Annotated[Literal["tmux", "t", "herdr", "h", "auto", "a"], typer.Option(..., "--backend", "-b", help="Backend multiplexer to use")] = "tmux",
        ) -> None:
    """Choose one or more session targets to kill."""
    if kill_all and name is not None:
        typer.echo("Error: --all cannot be used together with NAME.", err=True, color=True)
        raise typer.Exit(code=1)
    if kill_all and window:
        typer.echo("Error: --all cannot be used together with --window.", err=True, color=True)
        raise typer.Exit(code=1)
    if name is not None and window:
        typer.echo("Error: --window can only be used when NAME is omitted.", err=True, color=True)
        raise typer.Exit(code=1)
    if idle and window:
        typer.echo("Error: --idle cannot be used together with --window.", err=True, color=True)
        raise typer.Exit(code=1)
    from stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers import print_kill_summary, resolve_session_backend
    backend_resolved = resolve_session_backend(backend)
    from stackops.scripts.python.helpers.helpers_sessions.kill_impl import choose_kill_target as impl

    action, payload, killed_targets = impl(
        backend=backend_resolved,
        name=name,
        kill_all=kill_all,
        idle=idle,
        window=window,
    )
    if action == "error":
        typer.echo(payload, err=True, color=True)
        raise typer.Exit(code=1)
    if action == "run_script":
        if payload is None or payload.strip() == "":
            typer.echo("Error: kill operation did not return a final script.", err=True, color=True)
            raise typer.Exit(code=1)
        script = payload
        if backend_resolved == "tmux":
            from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution import (
                run_tmux_script,
            )

            try:
                run_tmux_script(
                    script=script,
                    timeout_seconds=30.0,
                )
                print_kill_summary(script=script, killed_targets=killed_targets)
                return
            except RuntimeError as error:
                typer.echo(f"Error: {error}", err=True, color=True)
                raise typer.Exit(code=1) from error
        from stackops.utils.code import exit_then_run_shell_script

        print_kill_summary(script=script, killed_targets=killed_targets)
        exit_then_run_shell_script(script=script, strict=True)
        return
    typer.echo("Error: kill operation did not return a final script.", err=True, color=True)
    raise typer.Exit(code=1)



def get_session_tabs() -> list[tuple[str, str]]:
    """Get all session tabs."""
    from stackops.scripts.python.helpers.helpers_sessions.attach_impl import get_session_tabs as impl
    result = impl()
    print(result)
    return result
def create_template(
    name: Annotated[str | None, typer.Argument(help="Name of the layout template to create")] = None,
    num_tabs: Annotated[int, typer.Option(..., "--num-tabs", "-t", min=1, help="Number of tabs to include in the template")] = 3,
) -> None:
    """Create a layout template file."""
    from stackops.scripts.python.helpers.helpers_sessions.utils import create_template as impl
    impl(name=name, num_tabs=num_tabs)

def create_from_function(
    num_process: Annotated[int, typer.Option(..., "--num-process", "-n", help="Number of parallel processes to run")],
    path: Annotated[str, typer.Option(..., "--path", "-p", help="Path to a Python or Shell script file or a directory containing such files")] = ".",
    function: Annotated[str | None, typer.Option(..., "--function", "-f", help="Function to run from the Python file. If not provided, you will be prompted to choose.")] = None,
) -> None:
    """Create a layout from a function to run in multiple processes."""
    from stackops.scripts.python.helpers.helpers_sessions.sessions_multiprocess import create_from_function as impl
    impl(num_process=num_process, path=path, function=function)



def trace(
    session_name: Annotated[str | None, typer.Argument(help="Name of the tmux session to trace. Required unless --interactive is set.")] = None,
    every: Annotated[float, typer.Option("--every", "-e", help="Polling interval in seconds between tmux checks")] = 10.0,
    until: Annotated[Literal["idle-shell", "all-exited", "exit-code", "session-missing"], typer.Option("--until", "-u", help="Stop only when the selected criterion is satisfied")] = "idle-shell",
    exit_code: Annotated[int | None, typer.Option("--exit-code", "-c", help="Required pane exit code when `--until exit-code` is selected")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose an existing tmux session interactively")] = False,
) -> None:
    """Trace a tmux session until every target matches a strict stop criterion."""
    from stackops.scripts.python.helpers.helpers_sessions.sessions_trace import trace_session as impl

    if every <= 0:
        typer.echo("Error: --every must be greater than 0.", err=True, color=True)
        raise typer.Exit(code=1)
    if until == "exit-code" and exit_code is None:
        typer.echo("Error: --exit-code is required when --until exit-code is selected.", err=True, color=True)
        raise typer.Exit(code=1)
    if until != "exit-code" and exit_code is not None:
        typer.echo("Error: --exit-code can only be used with --until exit-code.", err=True, color=True)
        raise typer.Exit(code=1)
    if session_name is not None and interactive:
        typer.echo("Error: SESSION_NAME cannot be used together with --interactive.", err=True, color=True)
        raise typer.Exit(code=1)
    if session_name is None:
        if not interactive:
            typer.echo("Error: SESSION_NAME is required unless --interactive is set.", err=True, color=True)
            raise typer.Exit(code=1)
        from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_existing_session_name

        action, payload = choose_existing_session_name(msg="Choose a tmux session to trace:")
        if action == "error":
            typer.echo(f"Error: {payload}", err=True, color=True)
            raise typer.Exit(code=1)
        session_name = payload

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
    agent: Annotated[str | None, typer.Option("--agent", "-a", help="AoE tool/agent name. Defaults to codex so --model/--sandbox/--yolo are immediately useful.")] = "codex",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model forwarded to the underlying AoE/agent CLI when supported.")] = None,
    provider: Annotated[str | None, typer.Option("--provider", "-p", help="Provider forwarded to the underlying AoE/agent CLI when supported.")] = None,
    sandbox: Annotated[str | None, typer.Option("--sandbox", "-s", help="Convenience flag forwarded to the launched agent CLI as `--sandbox <value>` when supported.")] = None,
    yolo: Annotated[bool, typer.Option("--yolo", "-y", help="Enable AoE/agent YOLO mode when supported.")] = False,
    cmd: Annotated[str | None, typer.Option("--cmd", "-C", help="Override the launched agent binary/command.")] = None,
    args: Annotated[list[str] | None, typer.Option("--args", "-A", help="Repeatable extra argument forwarded to the launched agent CLI.")] = None,
    env: Annotated[list[str] | None, typer.Option("--env", "-e", help="Repeatable KEY=VALUE pair forwarded to AoE when supported.")] = None,
    force: Annotated[bool, typer.Option("--force", "-F", help="Pass force/overwrite to AoE when supported.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-d", help="Print generated `aoe add` commands instead of executing them.")] = False,
    aoe_bin: Annotated[str, typer.Option("--aoe-bin", "-b", help="AoE executable to invoke.")] = "aoe",
    tab_command_mode: Annotated[Literal["prompt", "cmd", "ignore"], typer.Option("--tab-command-mode", "-M", help="How to use each tab's `command` field: as the initial prompt, as an agent-command override, or ignore it.")] = "prompt",
    subsitute_home: Annotated[bool, typer.Option(..., "--substitute-home", "-H", help="Substitute ~ and $HOME in layout file with actual home directory path")] = False,
    launch: Annotated[bool, typer.Option("--no-launch", "-n", help="Create each AoE session without launching it immediately.")] = True,
) -> None:
    """Launch selected layout tabs as agent-of-empires sessions.

    Mapping:
    - layoutName -> aoe --group
    - tabName -> aoe --title
    - startDir -> aoe add <path>
    - command -> initial prompt by default
    """
    from stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_aoe import run_aoe_cli as impl
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
    from stackops.scripts.python.terminal_summary import summary
    from stackops.scripts.python.terminal_summarize import summarize

    layouts_app = typer.Typer(help="Terminal management subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)

    layouts_app.command("run", no_args_is_help=True, help=run.__doc__, short_help="<r> Run the selected layout(s)")(run)
    layouts_app.command("r", no_args_is_help=True, help=run.__doc__, hidden=True)(run)

    layouts_app.command("run-all", no_args_is_help=True, help=run_all.__doc__, short_help="<R> Dynamically run every layout in a file")(run_all)
    layouts_app.command("R", no_args_is_help=True, help=run_all.__doc__, hidden=True)(run_all)
    
    layouts_app.command("run-aoe", no_args_is_help=True, help=run_aoe.__doc__, short_help="<e> Run selected layout(s) through agent-of-empires")(run_aoe)
    layouts_app.command("e", no_args_is_help=True, help=run_aoe.__doc__, hidden=True)(run_aoe)

    layouts_app.command("attach", no_args_is_help=False, help=attach_to_session.__doc__, short_help="<a> Attach to a session target")(attach_to_session)
    layouts_app.command("a", no_args_is_help=False, help=attach_to_session.__doc__, hidden=True)(attach_to_session)

    layouts_app.command("kill", no_args_is_help=False, help=kill_session_target.__doc__, short_help="<k> Kill a session target")(kill_session_target)
    layouts_app.command("k", no_args_is_help=False, help=kill_session_target.__doc__, hidden=True)(kill_session_target)

    layouts_app.command("trace", no_args_is_help=True, help=trace.__doc__, short_help="<t> Trace a tmux session until it settles")(trace)
    layouts_app.command("t", no_args_is_help=True, help=trace.__doc__, hidden=True)(trace)

    layouts_app.command("create-from-function", no_args_is_help=True, short_help="<c> Create a layout from a function")(create_from_function)
    layouts_app.command("c", no_args_is_help=True, hidden=True)(create_from_function)

    layouts_app.command("balance-load", no_args_is_help=True, help=balance_load.__doc__, short_help="<b> Balance the load across sessions")(balance_load)
    layouts_app.command("b", no_args_is_help=True, help=balance_load.__doc__, hidden=True)(balance_load)

    layouts_app.command("create-template", no_args_is_help=False, help=create_template.__doc__, short_help="<p> Create a layout template file")(create_template)
    layouts_app.command("p", no_args_is_help=False, help=create_template.__doc__, hidden=True)(create_template)

    layouts_app.command("summary", no_args_is_help=False, help=summary.__doc__, short_help="<s> Print running session summary")(summary)
    layouts_app.command("s", no_args_is_help=False, help=summary.__doc__, hidden=True)(summary)

    layouts_app.command("summarize", no_args_is_help=True, help=summarize.__doc__, short_help="<S> Summarize a layout file")(summarize)
    layouts_app.command("S", no_args_is_help=True, help=summarize.__doc__, hidden=True)(summarize)
    return layouts_app


def main() -> None:
    layouts_app = get_app()
    layouts_app()


if __name__ == "__main__":
    main()
