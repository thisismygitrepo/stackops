from typing import TYPE_CHECKING, Annotated, cast, get_args

import typer
from stackops.utils.cli_utils.interaction import require_interactive
from stackops.scripts.python.helpers.helpers_agents.agents_json import emit_agent_json

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_TECH_NAMES,
    BROWSER_TECH_NAMES_WITHOUT_AGENT,
    BrowserName,
    BrowserRuntimeOption,
    BrowserTechName,
    BrowserTechSelection,
    ChromiumBrowserName,
    DEFAULT_BROWSER_PORT,
    DEFAULT_BROWSER_PROFILE_PORT_START,
    ProfileBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_skill_types import SKILL_INSTALL_COMMAND_BACKEND
from stackops.utils.default_multiplexer import DEFAULT_SESSION_MULTIPLEXER_HELP
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

if TYPE_CHECKING:
    from stackops.utils.network.address import InterfaceIPv4Address


def install_tech(
    tool: Annotated[
        BrowserTechSelection,
        typer.Option(
            "--tool",
            "-w",
            help=("Browser automation tech: agent-browser, browser-use, pinchtab, playwright-cli, chrome-devtools-mcp, playwright-mcp, omp, or all."),
            case_sensitive=False,
            show_choices=True,
        ),
    ] = "agent-browser",
    agent: Annotated[
        AGENTS | None,
        typer.Option(
            "--agent",
            "-a",
            help="Agent to receive the browser skill or MCP configuration guidance; not used by omp. Omit to choose interactively.",
            case_sensitive=False,
            show_choices=True,
        ),
    ] = None,
    backend: Annotated[
        SKILL_INSTALL_COMMAND_BACKEND,
        typer.Option(
            "--backend", "-b", help="Upstream skills CLI runner used by agent-browser and pinchtab.", case_sensitive=False, show_choices=True
        ),
    ] = "npx",
) -> None:
    """Install browser automation CLI, MCP support, or a browser-capable agent."""
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import install_browser_tech

    try:
        selected_technologies: tuple[BrowserTechName, ...] = BROWSER_TECH_NAMES if tool == "all" else (tool,)
        resolved_agent = agent
        if resolved_agent is None and any(technology not in BROWSER_TECH_NAMES_WITHOUT_AGENT for technology in selected_technologies):
            require_interactive("Choosing a browser agent; supply --agent")
            from stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import choose_required_option, order_current_first
            from stackops.utils.default_agent import resolve_agent

            agent_options = cast(tuple[AGENTS, ...], get_args(AGENTS))
            resolved_agent = cast(
                AGENTS,
                choose_required_option(options=order_current_first(options=agent_options, current=resolve_agent(agent=None)), msg="Choose agent", header="Agent"),
            )
        results = tuple(
            install_browser_tech(which=selected_technology, agent=resolved_agent, backend=backend) for selected_technology in selected_technologies
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    for result in results:
        typer.echo(f"Prepared {result.which} in: {result.install_root}")
        for command in result.commands:
            typer.echo(f"Ran: {' '.join(command)}")
        for guide_path in result.guide_paths:
            typer.echo(f"Wrote: {guide_path}")
        if len(result.mcp_servers) > 0:
            typer.echo(f"MCP catalog servers: {', '.join(result.mcp_servers)}")
            typer.echo(f"Install into an agent with: stackops agents add-mcp {','.join(result.mcp_servers)} --agent {resolved_agent} --scope workspace")


def _parse_profile_names(*, raw_profile: str) -> tuple[str, ...]:
    names = tuple(name.strip() for name in raw_profile.split(","))
    if any(name == "" for name in names):
        raise typer.BadParameter("--profile entries cannot be empty")
    if len(set(names)) != len(names):
        raise typer.BadParameter("--profile entries must be unique")
    return names


def launch_browser(
    port: Annotated[
        int, typer.Option("--port", "-p", help="Browser automation endpoint port; with multiple profiles, consecutive ports are used starting here.")
    ] = DEFAULT_BROWSER_PORT,
    browser: Annotated[
        BrowserName, typer.Option("--browser", "-b", help="Browser to launch for agent automation.", case_sensitive=False, show_choices=True)
    ] = "chrome",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-r",
            help=(
                "Comma-separated StackOps profiles under ~/data/browsers-profiles/<browser>/<profile>; each profile gets its own endpoint. "
                "Omit for a fresh port-scoped profile."
            ),
        ),
    ] = None,
    tmp: Annotated[bool, typer.Option("--tmp", "-t", help="Copy --profile to <profile>/.tmp/<random-alias> and launch the copy.")] = False,
    lan: Annotated[bool, typer.Option("--lan", "-l", help="Expose endpoints on 0.0.0.0 through a localhost relay.")] = False,
    runtime: Annotated[
        BrowserRuntimeOption | None,
        typer.Option(
            "--runtime",
            "-m",
            help=f"Where browser processes run: tmux/t, tuios/u, zellij/z (Zellij 0.45+), or detached/d background processes. {DEFAULT_SESSION_MULTIPLEXER_HELP}",
            case_sensitive=False,
        ),
    ] = None,
    attach: Annotated[bool, typer.Option("--attach", "-a", help="Attach to the launched browser window; not available with --runtime detached.")] = False,
    new_window: Annotated[
        bool,
        typer.Option(
            "--new-window",
            "-w",
            help="Claim a browser window per endpoint (not Safari): a browser that is already running gets a new window; its id and tabs are reported.",
        ),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print browser endpoint and launch records as JSON.")] = False,
) -> None:
    """Launch browser automation endpoints with isolated profiles when supported."""
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts import resolve_browser_runtime
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import ExistingBrowserLaunchResult, NewBrowserLaunchResult
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output import build_browser_launch_summary, build_browser_launches_summary
    from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher

    try:
        resolved_runtime = resolve_browser_runtime(runtime=runtime)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if new_window and get_browser_launcher(browser=browser).endpoint_protocol == "webdriver":
        raise typer.BadParameter(f"--new-window is not available for {browser}: its WebDriver endpoint has no browser windows to manage")
    if attach:
        if resolved_runtime == "detached" or json_output:
            raise typer.BadParameter("--attach cannot be combined with --runtime detached or --json")
        require_interactive("Attaching to a browser window")
    profile_names: tuple[str | None, ...] = (None,) if profile is None else _parse_profile_names(raw_profile=profile)
    lan_address: InterfaceIPv4Address | None = None
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppWindow
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_windows import claim_browser_window
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch import launch_browser as launch_browser_impl

        if lan:
            from stackops.utils.network.address import select_lan_interface_ipv4

            lan_address = select_lan_interface_ipv4(prefer_vpn=False)
            if lan_address is None:
                raise RuntimeError("Could not determine a local LAN IPv4 address for the browser endpoint.")
        results = tuple(
            launch_browser_impl(browser=browser, port=port + offset, profile_name=profile_name, temporary=tmp, lan=lan, runtime=resolved_runtime)
            for offset, profile_name in enumerate(profile_names)
        )
        browser_windows: tuple[BrowserAppWindow | None, ...] = tuple(
            claim_browser_window(browser=result.browser, port=result.browser_port, open_new=isinstance(result, ExistingBrowserLaunchResult))
            if new_window
            else None
            for result in results
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_json import browser_launch_receipt

        emit_agent_json(
            [
                browser_launch_receipt(result=result, browser_window=browser_window)
                for result, browser_window in zip(results, browser_windows, strict=True)
            ]
        )
        return
    console = Console()
    if len(results) == 1:
        console.print(build_browser_launch_summary(result=results[0], lan_address=lan_address))
    else:
        console.print(build_browser_launches_summary(results=results, lan_address=lan_address))
    for result, browser_window in zip(results, browser_windows, strict=True):
        if browser_window is not None:
            tab_ids = ", ".join(tab.tab_id for tab in browser_window.tabs)
            typer.echo(f"Browser window {browser_window.window_id} on port {result.port} · tab {tab_ids}")
    first_windows = next((result.windows for result in results if isinstance(result, NewBrowserLaunchResult) and result.windows is not None), None)
    if attach and first_windows is not None:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts import attach_browser_windows

        try:
            attach_browser_windows(handle=first_windows)
        except RuntimeError as error:
            typer.echo(f"Browser endpoint is running, but attachment failed: {error}", err=True)
            raise typer.Exit(code=1) from error


def close_browser(
    port: Annotated[
        int | None,
        typer.Option("--port", "-p", help="Port of the tracked browser automation endpoint to close. Defaults to 9331 when --profile is omitted."),
    ] = None,
    browser: Annotated[
        BrowserName, typer.Option("--browser", "-b", help="Browser whose tracked launch should be closed.", case_sensitive=False, show_choices=True)
    ] = "chrome",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-r",
            help="Comma-separated saved StackOps profiles under ~/data/browsers-profiles/<browser>/<profile> whose tracked launches should be closed.",
        ),
    ] = None,
    window: Annotated[
        str | None,
        typer.Option(
            "--window", "-w", help="Close only this browser window id (see status) on the --port endpoint; the browser and its other windows keep running."
        ),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print closed launch identities as JSON.")] = False,
) -> None:
    """Close one tracked browser endpoint by --port, its saved profiles by --profile, or one browser window by --window."""
    if window is not None:
        if profile is not None:
            raise typer.BadParameter("--window closes one window on the --port endpoint; it cannot be combined with --profile")
        window_port = DEFAULT_BROWSER_PORT if port is None else port
        try:
            from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_windows import close_browser_window

            closed_window = close_browser_window(browser=browser, port=window_port, window_id=window)
        except ValueError as error:
            raise typer.BadParameter(str(error)) from error
        except RuntimeError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from error
        if json_output:
            emit_agent_json(closed_window)
            return
        typer.echo(f"Closed {browser} window {closed_window.window_id} ({len(closed_window.tabs)} tab(s)) on port {window_port}; the browser keeps running.")
        return
    profile_names: tuple[str, ...] | None = None
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_close import (
            close_browser_launch,
            close_named_browser_profile_launches,
            describe_closed_runtimes,
        )

        if profile is not None:
            if port is not None:
                raise ValueError("Choose either --port or --profile, not both")
            profile_names = _parse_profile_names(raw_profile=profile)
            match browser:
                case "chrome" | "brave" | "edge" | "firefox":
                    result = close_named_browser_profile_launches(browser=browser, profile_names=profile_names)
                case "safari":
                    raise ValueError("Safari does not support saved profiles; close it with --port")
        else:
            result = close_browser_launch(browser=browser, port=DEFAULT_BROWSER_PORT if port is None else port)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        emit_agent_json(result)
        return
    if profile_names is not None:
        profile_label = ", ".join(profile_names)
        if not result.closed:
            typer.echo(f"No active {browser} saved-profile launches found for: {profile_label}.")
            return
        typer.echo(
            f"Closed {len(result.closed)} {browser} saved-profile launch(es) for {profile_label} ({describe_closed_runtimes(result=result)})."
        )
        return
    resolved_port = DEFAULT_BROWSER_PORT if port is None else port
    if not result.closed:
        typer.echo(f"No active {browser} launch found on port {resolved_port}.")
        return
    typer.echo(f"Closed {browser} launch on port {resolved_port} ({describe_closed_runtimes(result=result)}).")


def batch_launch(
    browser: Annotated[
        ProfileBrowserName,
        typer.Option("--browser", "-b", help="Browser whose saved profiles should all be launched.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    port_start: Annotated[
        int, typer.Option("--port-start", "--port", "-p", help="Base port for profile endpoints; p1 uses this value plus 1.")
    ] = DEFAULT_BROWSER_PROFILE_PORT_START,
    max_profiles: Annotated[
        int | None, typer.Option("--max-profiles", "--max", "-n", min=1, help="Maximum profiles to launch; fewer are used when fewer are available.")
    ] = None,
    lan: Annotated[bool, typer.Option("--lan", "-l", help="Expose endpoints on 0.0.0.0 through localhost relays.")] = False,
    runtime: Annotated[
        BrowserRuntimeOption | None,
        typer.Option(
            "--runtime",
            "-m",
            help=f"Where browser processes run: tmux/t, tuios/u, zellij/z (Zellij 0.45+), or detached/d background processes. {DEFAULT_SESSION_MULTIPLEXER_HELP}",
            case_sensitive=False,
        ),
    ] = None,
    attach: Annotated[
        bool, typer.Option("--attach", "-a", help="Attach to the first launched browser window; not available with --runtime detached.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print browser endpoint and launch records as JSON.")] = False,
) -> None:
    """Launch every saved profile for one browser on its assigned port."""
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts import resolve_browser_runtime
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import NewBrowserLaunchResult
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output import build_browser_launches_summary

    try:
        resolved_runtime = resolve_browser_runtime(runtime=runtime)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if attach:
        if resolved_runtime == "detached" or json_output:
            raise typer.BadParameter("--attach cannot be combined with --runtime detached or --json")
        require_interactive("Attaching to a browser window")
    lan_address: InterfaceIPv4Address | None = None
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_batch import build_browser_profile_launch_specs
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch import launch_browser as launch_browser_impl

        specs = build_browser_profile_launch_specs(browser=browser, port_start=port_start)
        if max_profiles is not None:
            specs = specs[:max_profiles]
        if lan:
            from stackops.utils.network.address import select_lan_interface_ipv4

            lan_address = select_lan_interface_ipv4(prefer_vpn=False)
            if lan_address is None:
                raise RuntimeError("Could not determine a local LAN IPv4 address for the browser endpoints.")
        results = tuple(
            launch_browser_impl(browser=spec.browser, port=spec.port, profile_name=spec.profile_name, temporary=False, lan=lan, runtime=resolved_runtime)
            for spec in specs
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_json import browser_launch_receipt

        emit_agent_json([browser_launch_receipt(result=result, browser_window=None) for result in results])
        return
    Console().print(build_browser_launches_summary(results=results, lan_address=lan_address))
    first_windows = next((result.windows for result in results if isinstance(result, NewBrowserLaunchResult) and result.windows is not None), None)
    if attach and first_windows is not None:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts import attach_browser_windows

        try:
            attach_browser_windows(handle=first_windows)
        except RuntimeError as error:
            typer.echo(f"Browser endpoints are running, but attachment failed: {error}", err=True)
            raise typer.Exit(code=1) from error


def batch_close(
    browser: Annotated[
        ProfileBrowserName,
        typer.Option(
            "--browser", "-b", help="Browser whose StackOps-tracked saved-profile launches should be closed.", case_sensitive=False, show_choices=True
        ),
    ] = "chrome",
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print closed launch identities as JSON.")] = False,
) -> None:
    """Close tracked saved-profile launches for one browser."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_close import close_all_browser_profile_launches, describe_closed_runtimes

        result = close_all_browser_profile_launches(browser=browser)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        emit_agent_json(result)
        return
    browser_label = browser.title()
    if not result.closed:
        typer.echo(f"No active {browser_label} saved-profile launches found.")
        return
    typer.echo(f"Closed {len(result.closed)} {browser_label} saved-profile launch(es) ({describe_closed_runtimes(result=result)}).")


def status(
    all_browsers: Annotated[
        bool, typer.Option("--all", "-a", help="Show every open browser, whether StackOps launched it or not, instead of tracked launches.")
    ] = False,
    browser: Annotated[
        BrowserName | None,
        typer.Option("--browser", "-b", help="Only show this browser. Omit to show all browsers.", case_sensitive=False, show_choices=True),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print collected browser status records as JSON.")] = False,
) -> None:
    """Show StackOps browser launches across tmux, tuios, zellij and detached runtimes."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_status import (
            collect_browser_launch_windows_status,
            collect_open_browser_status,
            show_browser_launch_status,
            show_open_browser_status,
        )

        if all_browsers:
            rows = tuple(row for row in collect_open_browser_status() if browser is None or row.browser.browser == browser)
            if json_output:
                emit_agent_json(rows)
            else:
                show_open_browser_status(rows=rows)
        else:
            statuses = tuple(status for status in collect_browser_launch_windows_status() if browser is None or status.launch.browser == browser)
            if json_output:
                emit_agent_json(statuses)
            else:
                show_browser_launch_status(statuses=statuses)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def list_profiles(
    sites: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Sites to check in every profile, e.g. google slack oracle. Each is matched as a case-insensitive part of the cookie host "
                "and reports the sign-in state, accounts, saved logins and last activity."
            )
        ),
    ] = None,
    browser: Annotated[
        ChromiumBrowserName,
        typer.Option("--browser", "-b", help="Chromium-family browser whose profiles should be listed.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    native: Annotated[
        bool,
        typer.Option("--native", "-n", help="List the browser's own profiles from its normal location instead of saved StackOps profiles."),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print the profile rows as JSON.")] = False,
) -> None:
    """List a browser's profiles with their state, browser account and what each is signed in to.

    Reads profile files only: cookie hosts, names and expiry, saved-login usernames and the browser's own account. Cookie values and
    passwords are never read or decrypted, so account names are known for Google (recorded by the browser) and for saved logins.
    """
    from datetime import UTC, datetime

    resolved_sites = tuple(site.strip() for site in sites or ())
    if any(site == "" for site in resolved_sites):
        raise typer.BadParameter("Sites cannot be empty")
    if len(set(resolved_sites)) != len(resolved_sites):
        raise typer.BadParameter("Sites must be unique")
    now = datetime.now(tz=UTC)
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory import collect_browser_profile_inventory

        rows = collect_browser_profile_inventory(browser=browser, native=native, sites=resolved_sites, now=now)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        emit_agent_json(rows)
        return
    from rich.console import Console

    from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_inventory_output import build_browser_profile_inventory_table

    Console().print(build_browser_profile_inventory_table(browser=browser, native=native, sites=resolved_sites, rows=rows, now=now))


def declutter(
    profile: Annotated[
        str | None, typer.Option("--profile", "-r", help="StackOps profile under ~/data/browsers-profiles/<browser>/<profile>. Omit with --all.")
    ] = None,
    browser: Annotated[
        ProfileBrowserName,
        typer.Option("--browser", "-b", help="Browser whose profile should be decluttered.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    all_profiles: Annotated[
        bool, typer.Option("--all", "-a", help="Declutter every saved profile for the browser instead of one --profile.")
    ] = False,
) -> None:
    """Remove rebuildable models and caches from closed browser profiles."""
    if profile is not None and all_profiles:
        raise typer.BadParameter("Choose either --profile or --all, not both")
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import declutter_all_browser_profiles, declutter_browser_profile

        if all_profiles:
            results = declutter_all_browser_profiles(browser=browser)
        elif profile is None:
            raise typer.BadParameter("Provide --profile or --all")
        else:
            results = (declutter_browser_profile(browser=browser, profile_name=profile),)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    total_recovered_bytes = 0
    for result in results:
        total_recovered_bytes += result.recovered_bytes
        typer.echo(f"Decluttered {browser} profile: {result.profile_path}")
        typer.echo(f"Removed paths: {len(result.removed_paths)}")
        typer.echo(f"Recovered: {_format_mebibytes(byte_count=result.recovered_bytes)} MiB")
        typer.echo(f"Profile size: {_format_mebibytes(byte_count=result.size_after_bytes)} MiB")
    typer.echo(f"Profiles decluttered: {len(results)}")
    typer.echo(f"Total recovered: {_format_mebibytes(byte_count=total_recovered_bytes)} MiB")


def replicate(
    count: Annotated[int, typer.Option("--count", "-c", min=1, help="Number of copies to create as p1, p2, ... pN when --target is omitted.")] = 1,
    target: Annotated[
        str | None, typer.Option("--target", "-t", help="Destination profile name or comma-separated names, e.g. work,personal. Copy count is inferred.")
    ] = None,
    browser: Annotated[
        ProfileBrowserName,
        typer.Option("--browser", "-b", help="Browser whose profile should be replicated.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-r",
            help="Source StackOps profile (default: base). With --native, use a browser profile name or folder; omit to choose from a table.",
        ),
    ] = None,
    native: Annotated[
        bool, typer.Option("--native", "-n", help="Copy a profile from the browser's normal location. Quit the browser before copying.")
    ] = False,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-o", help="Delete existing destination profiles completely before copying the source profile.")
    ] = False,
) -> None:
    """Copy a closed StackOps or native browser profile to named destinations."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import replicate_browser_profile

        if target is None:
            target_names = tuple(f"""p{index}""" for index in range(1, count + 1))
        else:
            if count != 1:
                raise typer.BadParameter("Use either --target or --count; --target sets the number of copies")
            target_names = tuple(name.strip() for name in target.split(","))
            if any(name == "" for name in target_names):
                raise typer.BadParameter("--target entries cannot be empty")
            if len(set(target_names)) != len(target_names):
                raise typer.BadParameter("--target entries must be unique")

        if native:
            from stackops.scripts.python.helpers.helpers_agents.agents_browser_native_replication import replicate_native_browser_profile
            from stackops.scripts.python.helpers.helpers_agents.agents_browser_native_selection import select_native_browser_profile

            selected_profile = select_native_browser_profile(browser=browser, profile_name=profile)
            typer.echo(f"Native source: {selected_profile.name} ({selected_profile.profile_path})")
            result = replicate_native_browser_profile(browser=browser, profile=selected_profile, target_names=target_names, overwrite=overwrite)
        else:
            result = replicate_browser_profile(
                browser=browser, profile_name="base" if profile is None else profile, target_names=target_names, overwrite=overwrite
            )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Replicated {browser} profile: {result.source_path}")
    for destination_path in result.destination_paths:
        typer.echo(f"Created: {destination_path}")
    typer.echo(f"Source size: {_format_mebibytes(byte_count=result.source_size_bytes)} MiB")


def _format_mebibytes(*, byte_count: int) -> str:
    return f"{byte_count / (1024 * 1024):,.1f}"


def get_app() -> typer.Typer:
    browser_app = typer.Typer(
        help="🌐 <b> Browser automation for agent CLIs and MCP", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    browser_app.command(name="install", no_args_is_help=False, short_help="📦 <i> Install browser tools or prepare MCP setup guides")(
        install_tech
    )
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(install_tech)
    browser_app.command(name="launch", no_args_is_help=False, short_help="🚀 <l> Launch browser automation endpoint")(launch_browser)
    browser_app.command(name="l", no_args_is_help=False, hidden=True)(launch_browser)
    browser_app.command(name="close", no_args_is_help=False, short_help="❌ <c> Close tracked endpoints by port or profile names")(close_browser)
    browser_app.command(name="c", no_args_is_help=False, hidden=True)(close_browser)
    browser_app.command(name="batch-launch", no_args_is_help=False, short_help="🚀 <L> Launch every saved profile for one browser")(batch_launch)
    browser_app.command(name="L", no_args_is_help=False, hidden=True)(batch_launch)
    browser_app.command(name="batch-close", no_args_is_help=False, short_help="❌ <C> Close tracked saved-profile browser launches")(batch_close)
    browser_app.command(name="C", no_args_is_help=False, hidden=True)(batch_close)
    browser_app.command(name="status", no_args_is_help=False, short_help="📊 <s> Show active browser launches")(status)
    browser_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    browser_app.command(name="profiles", no_args_is_help=False, short_help="🪪 <p> List profiles and what each is signed in to")(list_profiles)
    browser_app.command(name="p", no_args_is_help=False, hidden=True)(list_profiles)
    browser_app.command(name="declutter", no_args_is_help=False, short_help="🧹 <d> Remove rebuildable browser profile data")(declutter)
    browser_app.command(name="d", no_args_is_help=False, hidden=True)(declutter)
    browser_app.command(name="replicate", no_args_is_help=True, short_help="🧬 <r> Copy a StackOps or native profile to named destinations")(replicate)
    browser_app.command(name="r", no_args_is_help=True, hidden=True)(replicate)
    return browser_app
