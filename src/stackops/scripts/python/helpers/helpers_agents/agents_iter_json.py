import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from time import sleep

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_agent_ops_cache import clean_agent_ops_cache
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import WorkspaceId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_service import close_iter_workspace_plans, load_active_workspace_ids, plan_iter_workspace_closes
from stackops.scripts.python.helpers.helpers_agents.agents_json import emit_agent_json, serialize_agent_result


def clean_iter_json(*, cwd: Path, workspace_id: str | None, dry_run: bool) -> None:
    with redirect_stdout(sys.stderr):
        result = clean_agent_ops_cache(
            cwd=cwd, workspace_id=WorkspaceId(workspace_id) if workspace_id is not None else None,
            dry_run=dry_run, load_active_workspace_ids=load_active_workspace_ids,
            report=lambda message: typer.echo(message, err=True),
        )
    emit_agent_json(result)


def close_iter_json(*, workspace_id: str | None, continuous: bool, retain_previous: int, dry_run: bool, interval_seconds: int) -> None:
    while True:
        with redirect_stdout(sys.stderr):
            plans = plan_iter_workspace_closes(workspace_id=workspace_id, retain_previous=retain_previous)
            results = () if dry_run else close_iter_workspace_plans(close_plans=plans, report=lambda message: typer.echo(message, err=True))
        typer.echo(json.dumps({"dry_run": dry_run, "plans": plans, "results": results}, default=serialize_agent_result))
        if any(result.failed_tabs for result in results) and not continuous:
            raise RuntimeError("Failed to close iteration tabs; see JSON results.")
        if dry_run or not continuous:
            return
        sleep(interval_seconds)
