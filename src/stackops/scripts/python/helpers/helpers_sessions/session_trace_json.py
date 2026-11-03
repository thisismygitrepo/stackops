import json
import sys
from contextlib import redirect_stdout
from time import monotonic, sleep

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_json import serialize_agent_result
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget
from stackops.scripts.python.helpers.helpers_sessions.session_trace_kill import build_trace_kill_plan, execute_trace_kill_plan
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import TraceSnapshot, TraceUntil
from stackops.scripts.python.helpers.helpers_sessions.session_trace_runner import TraceSnapshotLoader
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer


def trace_json_events(
    *, backend: SessionMultiplexer, session_names: list[str], until: TraceUntil, every_seconds: float,
    exit_code: int | None, kill: bool, snapshot_loader: TraceSnapshotLoader,
) -> None:
    started_at = monotonic()
    attempt = 0
    completed: set[str] = set()
    latest: dict[str, TraceSnapshot] = {}
    killed: list[KilledTarget] = []
    try:
        while True:
            attempt += 1
            active_names = [name for name in session_names if name not in completed]
            with redirect_stdout(sys.stderr):
                snapshots = tuple(snapshot_loader(name, until, exit_code) for name in active_names)
                for name, snapshot in zip(active_names, snapshots, strict=True):
                    if snapshot.session_name != name:
                        raise ValueError(f"Trace loader returned {snapshot.session_name!r} for {name!r}")
                    latest[name] = snapshot
                if kill:
                    plan = build_trace_kill_plan(backend=backend, snapshots=snapshots)
                    execute_trace_kill_plan(plan=plan)
                    killed.extend(command.summary for command in plan.commands)
                    completed.update(plan.completed_session_names)
            done = len(completed) == len(session_names) if kill else all(snapshot.criterion_satisfied for snapshot in latest.values())
            typer.echo(json.dumps({
                "event": "complete" if done else "snapshot", "backend": backend, "until": until,
                "attempt": attempt, "elapsed_seconds": monotonic() - started_at,
                "sessions": [latest[name] for name in session_names], "killed_targets": killed,
            }, default=serialize_agent_result))
            if done:
                return
            sleep(every_seconds)
    except KeyboardInterrupt as error:
        typer.echo(json.dumps({"event": "interrupted", "attempt": attempt}))
        raise typer.Exit(code=130) from error
    except (NotImplementedError, ValueError, RuntimeError, OSError) as error:
        typer.echo(json.dumps({"event": "error", "error": str(error), "attempt": attempt}))
        raise typer.Exit(code=1) from error
