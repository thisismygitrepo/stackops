from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import CleanCategory, CleanOutcome, Risk
from stackops.utils.cli_utils.interaction import require_interactive


def clean_drive(
    dry_run: Annotated[bool, typer.Option("--dry-run", "-d", help="Scan and report estimated savings only; never deletes.")] = False,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Pick targets of any risk in a fuzzy multi-select, then confirm.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Clean the selected (●) targets without asking.")] = False,
    list_targets: Annotated[bool, typer.Option("--list", "-l", help="List the targets and the free space without measuring anything; never deletes.")] = False,
    target: Annotated[
        list[str] | None,
        typer.Option("--target", "-t", help="Only this target key (see --list); repeatable. Explicit targets ignore --max-risk and --sudo."),
    ] = None,
    category: Annotated[
        list[CleanCategory] | None,
        typer.Option("--category", "-c", case_sensitive=False, help="Only targets in this category; repeatable."),
    ] = None,
    exclude: Annotated[list[str] | None, typer.Option("--exclude", "-x", help="Skip this target key; repeatable.")] = None,
    max_risk: Annotated[Risk, typer.Option("--max-risk", "-r", help="Highest risk level selected automatically.")] = "safe",
    sudo: Annotated[bool, typer.Option("--sudo", "-s", help="Also select targets that need root/admin; runs them through sudo on Linux and macOS.")] = False,
    search_root: Annotated[
        list[Path] | None,
        typer.Option("--root", "-R", exists=True, file_okay=False, help="Where to look for project folders (.ai, node_modules, .venv, ...); repeatable. Default: home."),
    ] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Print JSON records; requires --dry-run, --list or --yes.")] = False,
) -> None:
    if dry_run and (interactive or yes):
        raise typer.BadParameter("--dry-run cannot be combined with --interactive or --yes.", param_hint="--dry-run")
    if list_targets and (dry_run or interactive or yes):
        raise typer.BadParameter("--list cannot be combined with --dry-run, --interactive or --yes.", param_hint="--list")
    if interactive and yes:
        raise typer.BadParameter("--interactive already asks for confirmation; drop --yes.", param_hint="--interactive")
    if output_json and not (dry_run or list_targets or yes):
        raise typer.BadParameter("--json requires --dry-run, --list or --yes.", param_hint="--json")
    if not (dry_run or list_targets or yes):
        require_interactive("Choosing and confirming a drive cleanup; pass --yes to clean the selection or --dry-run to only report")
    import json
    import shutil

    from rich.console import Console
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_utils.clean_drive_execute import clean_target, is_elevated
    from stackops.scripts.python.helpers.helpers_utils.clean_drive_render import (
        catalog_record,
        describe_action,
        format_estimate,
        outcome_records,
        render_catalog,
        render_outcomes,
        render_report,
        scan_records,
    )
    from stackops.scripts.python.helpers.helpers_utils.clean_drive_scan import current_platform, scan_scope, select_scope, total_estimate

    platform = current_platform()
    try:
        scope, auto_keys = select_scope(
            platform=platform, targets=target or [], categories=category or [], excludes=exclude or [], max_risk=max_risk, allow_root=sudo,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    console = Console(stderr=output_json)
    if list_targets:
        disk = shutil.disk_usage(Path.home())
        catalog = catalog_record(scope=scope, auto_keys=auto_keys, free_bytes=disk.free, total_bytes=disk.total)
        if output_json:
            typer.echo(json.dumps(catalog, indent=2))
        else:
            render_catalog(console=console, record=catalog)
        return
    elevated = is_elevated()
    roots = tuple(path.expanduser().resolve() for path in search_root) if search_root is not None else (Path.home(),)
    with console.status(f"""Measuring {len(scope)} cleanup target(s)…"""):
        scans = scan_scope(scope=scope, roots=roots)
    if output_json and dry_run:
        typer.echo(json.dumps(scan_records(scans=scans, auto_keys=auto_keys), indent=2))
        return
    render_report(console=console, scans=scans, auto_keys=auto_keys, elevated=elevated)
    if dry_run:
        console.print(Text("Dry run: nothing was deleted. Clean with -i to pick, -y for the ● selection, or -t KEY for specific targets.", style="dim"))
        return
    if interactive:
        from stackops.scripts.python.helpers.helpers_utils.clean_drive_interactive import pick_scans

        chosen = pick_scans(scans=scans, elevated=elevated)
    else:
        chosen = [scan for scan in scans if scan.status == "ready" and scan.target.key in auto_keys]
    if not chosen:
        console.print("Nothing selected to clean.")
        if output_json:
            typer.echo("[]")
        return
    if not yes:
        names = ", ".join(scan.target.key for scan in chosen)
        if not typer.confirm(f"""Permanently clean {names} (about {format_estimate(total_estimate(chosen))})?""", default=False):
            console.print("Cancelled; nothing was deleted.")
            return
    free_before = shutil.disk_usage(Path.home()).free
    outcomes: list[CleanOutcome] = []
    for scan in chosen:
        console.print(f"""Cleaning {scan.target.key}: {describe_action(scan=scan, elevated=elevated)}""")
        outcomes.append(clean_target(scan=scan, elevated=elevated, platform=platform))
    free_after = shutil.disk_usage(Path.home()).free
    if output_json:
        typer.echo(json.dumps(outcome_records(outcomes), indent=2))
    else:
        render_outcomes(console=console, outcomes=outcomes, free_before=free_before, free_after=free_after)
    if any(outcome.status == "failed" for outcome in outcomes):
        raise typer.Exit(1)
