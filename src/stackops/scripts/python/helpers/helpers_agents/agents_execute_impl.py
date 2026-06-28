import shlex
import subprocess
from collections.abc import Callable
from pathlib import Path
from platform import system
from time import sleep
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_execute_models import (
    ADVANCE_STATUSES,
    READY_STATUSES,
    PlanDocument,
    PlanPhase,
    read_plan_document,
    write_plan_document,
)
from stackops.scripts.python.helpers.helpers_agents.agents_execute_prompts import write_completion_check_prompt, write_phase_launch_prompt
from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


EXECUTE_INTERVAL_SECONDS: Final[int] = 300


def run_execute(*, plan_path: Path, checker_agent: AGENTS, interval_seconds: int, once: bool, report: Callable[[str], None]) -> None:
    if interval_seconds < 1:
        raise ValueError("--interval must be at least 1 second")
    while True:
        execute_plan_once(plan_path=plan_path, checker_agent=checker_agent, report=report)
        if once:
            return
        report(f"Next execute pass in {interval_seconds} second(s).")
        sleep(interval_seconds)


def execute_plan_once(*, plan_path: Path, checker_agent: AGENTS, report: Callable[[str], None]) -> None:
    resolved_plan_path = plan_path.expanduser().resolve()
    plan = read_plan_document(plan_path=resolved_plan_path)
    phase_index = _first_actionable_phase_index(plan=plan)
    if phase_index is None:
        report(f"{resolved_plan_path}: no pending, ready, running, or blocked phases.")
        return

    phase = plan["phases"][phase_index]
    match phase["status"]:
        case "running":
            if not ask_phase_finished(plan=plan, phase=phase, plan_path=resolved_plan_path, checker_agent=checker_agent):
                report(f"{phase['id']}: still running.")
                return
            phase["status"] = "completed"
            write_plan_document(plan_path=resolved_plan_path, plan=plan)
            report(f"{phase['id']}: marked completed.")
            next_phase = _first_ready_phase(plan=plan)
            if next_phase is None:
                report(f"{resolved_plan_path}: plan has no next ready phase.")
                return
            next_phase["status"] = "running"
            write_plan_document(plan_path=resolved_plan_path, plan=plan)
            launch_phase_agent(plan=plan, phase=next_phase, plan_path=resolved_plan_path)
            report(f"{next_phase['id']}: launched and marked running.")
        case "pending" | "ready":
            phase["status"] = "running"
            write_plan_document(plan_path=resolved_plan_path, plan=plan)
            launch_phase_agent(plan=plan, phase=phase, plan_path=resolved_plan_path)
            report(f"{phase['id']}: launched and marked running.")
        case "blocked" | "cancelled":
            report(f"{phase['id']}: status is {phase['status']}; executor will not launch later phases.")
        case "completed" | "skipped":
            report(f"{phase['id']}: already {phase['status']}.")
        case _:
            raise ValueError(f"{phase['id']}: unsupported status {phase['status']}")


def ask_phase_finished(*, plan: PlanDocument, phase: PlanPhase, plan_path: Path, checker_agent: AGENTS) -> bool:
    prompt_path = write_completion_check_prompt(plan=plan, phase=phase, plan_path=plan_path)
    command_line = build_agent_command(agent=checker_agent, prompt_file=prompt_path, reasoning_effort=None)
    output = _run_shell_command_capture(command_line=command_line)
    return parse_agent_boolean(output=output)


def launch_phase_agent(*, plan: PlanDocument, phase: PlanPhase, plan_path: Path) -> int:
    prompt_path = write_phase_launch_prompt(plan=plan, phase=phase, plan_path=plan_path)
    command_line = build_agent_command(agent=phase["agent"], prompt_file=prompt_path, reasoning_effort=None)
    process = _start_shell_command(command_line=command_line)
    return process.pid


def parse_agent_boolean(*, output: str) -> bool:
    normalized = output.strip().lower()
    match normalized:
        case "true":
            return True
        case "false":
            return False
        case _:
            raise ValueError(f"Completion checker must return exactly true or false, got: {output.strip()!r}")


def _first_actionable_phase_index(*, plan: PlanDocument) -> int | None:
    for index, phase in enumerate(plan["phases"]):
        if phase["status"] in ADVANCE_STATUSES:
            continue
        return index
    return None


def _first_ready_phase(*, plan: PlanDocument) -> PlanPhase | None:
    for phase in plan["phases"]:
        if phase["status"] in READY_STATUSES:
            return phase
    return None


def _run_shell_command_capture(*, command_line: str) -> str:
    command = _shell_command(command_line=command_line)
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.returncode == 0:
        return result.stdout
    detail = (result.stderr or result.stdout or "unknown error").strip()
    raise RuntimeError(f"Agent command failed ({shlex.join(command)}): {detail}")


def _start_shell_command(*, command_line: str) -> subprocess.Popen[str]:
    command = _shell_command(command_line=command_line)
    return subprocess.Popen(command, text=True)


def _shell_command(*, command_line: str) -> list[str]:
    if system() == "Windows":
        return ["powershell", "-NoProfile", "-Command", command_line]
    return ["bash", "-lc", command_line]

