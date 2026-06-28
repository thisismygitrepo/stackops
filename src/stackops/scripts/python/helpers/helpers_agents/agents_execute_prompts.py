import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_execute_models import PlanDocument, PlanPhase


def build_phase_launch_prompt(*, plan: PlanDocument, phase: PlanPhase, plan_path: Path) -> str:
    agentops_line = "No agentops operation is declared for this phase."
    if phase["agentOps"] is not None:
        agentops_line = f"This phase declares agentops operation `{phase['agentOps']}`. Use skill agentops and follow that operation's rules."
    return f"""Execute one StackOps plan phase.

Plan path:
{plan_path}

Plan objective:
{plan["objective"]}

Phase:
{json.dumps(phase, ensure_ascii=False, indent=2)}

{agentops_line}

Rules:
- Execute only this phase.
- Do not edit the plan JSON; the executor owns phase status updates.
- Verify local state before editing.
- Leave durable evidence in the repository or Herdr-managed agent records so a separate checker can decide whether this phase is complete.
- If work must continue in another interactive agent, use skill agentops handover.
"""


def build_completion_check_prompt(*, plan: PlanDocument, phase: PlanPhase, plan_path: Path) -> str:
    return f"""Decide whether one StackOps plan phase is complete.

Plan path:
{plan_path}

Plan objective:
{plan["objective"]}

Phase to check:
{json.dumps(phase, ensure_ascii=False, indent=2)}

Return exactly one lowercase JSON boolean token:
true
or
false

Return true only when the phase task is actually complete and there is concrete local or Herdr-visible evidence.
Return false when the phase is still running, blocked, uncertain, or lacks evidence.
Do not explain your answer.
"""


def write_phase_launch_prompt(*, plan: PlanDocument, phase: PlanPhase, plan_path: Path) -> Path:
    prompt_path = execute_records_root(plan_path=plan_path) / "agents" / phase["id"] / "task.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_phase_launch_prompt(plan=plan, phase=phase, plan_path=plan_path), encoding="utf-8")
    return prompt_path


def write_completion_check_prompt(*, plan: PlanDocument, phase: PlanPhase, plan_path: Path) -> Path:
    prompt_path = execute_records_root(plan_path=plan_path) / "checks" / f"{phase['id']}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_completion_check_prompt(plan=plan, phase=phase, plan_path=plan_path), encoding="utf-8")
    return prompt_path


def execute_records_root(*, plan_path: Path) -> Path:
    slug = plan_path.name.removesuffix(".plan.json")
    if plan_path.parent.name == "plans" and plan_path.parent.parent.name == ".ai":
        return plan_path.parent.parent / "agentops" / "execute" / slug
    return plan_path.parent / ".ai" / "agentops" / "execute" / slug
