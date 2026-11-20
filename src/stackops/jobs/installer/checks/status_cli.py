from pathlib import Path
from typing import Annotated

import typer

from stackops.jobs.installer.checks.constants import SECURITY_RECORDS_ROOT


def status(
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print the overview as JSON.")] = False,
    records_dir: Annotated[Path, typer.Option("--records-dir", "-d", help="Scan history directory")] = SECURITY_RECORDS_ROOT,
) -> None:
    import contextlib
    import sys

    from stackops.jobs.installer.checks.check_installations import collect_apps_to_scan
    from stackops.jobs.installer.checks.scan_history import list_runs
    from stackops.jobs.installer.checks.scan_overview import build_overview, summarize_run
    from stackops.secrets.readers import read_virus_total_api_keys

    records_dir = records_dir.expanduser().absolute()
    # Gathering the apps prints progress lines; they go to stderr so that stdout holds only the overview.
    with contextlib.redirect_stdout(sys.stderr):
        installed = collect_apps_to_scan(None)
    runs = list_runs(records_dir)
    apps = build_overview(runs, installed)
    account_count = 0
    account_problem: str | None = None
    try:
        account_count = len(read_virus_total_api_keys())
    except ValueError as exc:
        account_problem = str(exc)
    if json_output:
        import json

        typer.echo(
            json.dumps(
                {
                    "records_dir": str(records_dir),
                    "accounts": {"count": account_count, "problem": account_problem},
                    "runs": len(runs),
                    "latest_run": summarize_run(runs[0]) if runs else None,
                    "apps": apps,
                }
            )
        )
        return
    from rich.console import Console

    from stackops.jobs.installer.checks.security_helper import build_raw_csv_table

    rows: list[dict[str, object]] = [
        {
            "app_name": app["name"],
            "version": app["version"],
            "verdict": "changed since its check" if app["changed_since"] else app["verdict"].replace("_", " "),
            "flagged": f"""{app["flagged_engines"]}/{app["verdict_engines"]}""" if app["verdict_engines"] else None,
            "checked_at": app["checked_at"],
            "app_path": app["path"],
        }
        for app in apps
    ]
    Console().print(build_raw_csv_table("Installed Apps: Latest Scan Verdict", rows, ("app_name", "version", "verdict", "flagged", "checked_at", "app_path")))
    unchecked = sum(app["verdict"] == "unchecked" for app in apps)
    typer.echo(f"""{len(apps)} installed apps; {len(apps) - unchecked} with a saved result from {len(runs)} scan runs in {records_dir}.""")
    typer.echo(f"""VirusTotal accounts ready: {account_count}.""" if account_problem is None else f"""Scans cannot run: {account_problem}""")
