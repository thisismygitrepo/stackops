from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias, assert_never

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_t3_mcp import (
    JsonObject,
    T3McpSession,
    call_t3_tool,
    open_t3_mcp_session,
    require_t3_objects,
    require_t3_text,
)
from stackops.scripts.python.helpers.helpers_agents.constants import T3_REASONING_OPTION_IDS, T3_RUNTIME_MODE, T3_SERVER_URL, T3_TITLE_MAX_CHARS
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, HOST, PROVIDER, ReasoningEffort

T3Driver: TypeAlias = Literal["claudeAgent", "codex", "cursor", "opencode", "pi", "muse", "antigravity"]


@dataclass(frozen=True)
class T3LaunchTarget:
    driver: T3Driver
    model: str
    reasoning_effort: ReasoningEffort | None


def _t3_driver(agent: AGENTS) -> T3Driver | None:
    match agent:
        case "claude":
            return "claudeAgent"
        case "codex":
            return "codex"
        case "cursor-agent":
            return "cursor"
        case "opencode":
            return "opencode"
        case "pi":
            return "pi"
        case "muse":
            return "muse"
        case "agy":
            return "antigravity"
        case "qwen" | "copilot" | "cortex" | "deepseek" | "forge" | "crush" | "q" | "kilocode" | "cline" | "auggie" | "oz" | "droid" | "maki":
            return None
        case _:
            assert_never(agent)


def resolve_t3_launch_target(
    agent: AGENTS, host: HOST, provider: PROVIDER | None, model: str | None, reasoning_effort: ReasoningEffort | None
) -> T3LaunchTarget:
    if host != "local":
        raise ValueError("The t3 backend launches agents on the local T3 Code server, so --host must be local.")
    if provider is not None:
        raise ValueError("The t3 backend uses the provider configured in T3 Code; remove --provider.")
    if model is None:
        raise ValueError("The t3 backend requires --model: T3 Code needs an explicit model id for the selected agent.")
    driver = _t3_driver(agent=agent)
    if driver is None:
        raise ValueError(f"""T3 Code has no provider for agent '{agent}'. Use claude, codex, cursor-agent, opencode, pi, muse or agy.""")
    return T3LaunchTarget(driver=driver, model=model, reasoning_effort=reasoning_effort)


def _model_selection(capabilities: JsonObject, target: T3LaunchTarget) -> JsonObject:
    providers = [provider for provider in require_t3_objects(capabilities, "providers", "capabilities") if provider.get("driverKind") == target.driver]
    if len(providers) != 1:
        raise RuntimeError(f"""Expected one T3 Code provider instance for {target.driver}, found {len(providers)}.""")
    models = require_t3_objects(providers[0], "models", f"""provider {target.driver}""")
    matching = [model for model in models if model.get("id") == target.model]
    if len(matching) != 1:
        available = ", ".join(require_t3_text(model, "id", "model") for model in models)
        raise ValueError(f"""T3 Code provider {target.driver} has no model '{target.model}'. Available: {available}""")
    selection: JsonObject = {"instanceId": require_t3_text(providers[0], "providerInstanceId", "provider"), "model": target.model}
    if target.reasoning_effort is None:
        return selection
    reasoning_options = [option for option in require_t3_objects(matching[0], "options", "model") if option.get("id") in T3_REASONING_OPTION_IDS]
    if len(reasoning_options) != 1:
        raise ValueError(f"""T3 Code model '{target.model}' has no reasoning option, so --reasoning is not supported.""")
    choices = [require_t3_text(choice, "id", "reasoning choice") for choice in require_t3_objects(reasoning_options[0], "options", "reasoning option")]
    if target.reasoning_effort not in choices:
        raise ValueError(f"""T3 Code model '{target.model}' supports reasoning {", ".join(choices)}, not '{target.reasoning_effort}'.""")
    option_id = require_t3_text(reasoning_options[0], "id", "reasoning option")
    return {**selection, "options": [{"id": option_id, "value": target.reasoning_effort}]}


def _project_id(session: T3McpSession, workspace_root: Path) -> str:
    cursor: object = None
    while True:
        page = call_t3_tool(session=session, name="t3_project_list", arguments={} if cursor is None else {"cursor": cursor})
        for project in require_t3_objects(page, "projects", "project list"):
            if Path(require_t3_text(project, "workspaceRoot", "project")).resolve() == workspace_root.resolve():
                return require_t3_text(project, "id", "project")
        cursor = page.get("nextCursor")
        if cursor is None:
            break
    created = call_t3_tool(session=session, name="t3_project_create", arguments={"title": workspace_root.name, "workspaceRoot": str(workspace_root)})
    project_id = require_t3_text(created, "id", "created project")
    typer.echo(f"""Registered {workspace_root} as T3 Code project {project_id}.""")
    return project_id


@dataclass(frozen=True)
class T3ThreadRequest:
    title: str
    message: str


def t3_requests_from_prompt_directories(job_name: str, prompt_directories: list[Path]) -> list[T3ThreadRequest]:
    from stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch import get_agent_prompt_file

    return [
        T3ThreadRequest(
            title=f"""{job_name}-{prompt_directory.name.split("_")[-1]}""",
            message=get_agent_prompt_file(prompt_directory=prompt_directory).read_text(encoding="utf-8"),
        )
        for prompt_directory in prompt_directories
    ]


def launch_t3_threads(workspace_root: Path, requests: list[T3ThreadRequest], target: T3LaunchTarget) -> None:
    with open_t3_mcp_session(access=T3_RUNTIME_MODE) as session:
        capabilities = call_t3_tool(session=session, name="orchestrator_capabilities", arguments={})
        if capabilities.get("runtimeMode") != T3_RUNTIME_MODE:
            raise RuntimeError(f"""T3 Code granted runtime mode {capabilities.get("runtimeMode")!r}, expected {T3_RUNTIME_MODE}.""")
        model_selection = _model_selection(capabilities=capabilities, target=target)
        project_id = _project_id(session=session, workspace_root=workspace_root)
        for request in requests:
            launched = call_t3_tool(
                session=session,
                name="t3_thread_launch",
                arguments={
                    "title": request.title,
                    "projectId": project_id,
                    "modelSelection": model_selection,
                    "runtimeMode": T3_RUNTIME_MODE,
                    "message": request.message,
                },
            )
            typer.echo(f"""Launched {request.title} in T3 Code: thread {require_t3_text(launched, "threadId", "launch")} ({launched.get("status")}).""")
    typer.echo(f"""Follow up and monitor in T3 Code at {T3_SERVER_URL}.""")


def launch_prompt_file_in_t3(prompt_file: Path, workspace_root: Path, target: T3LaunchTarget) -> None:
    message = prompt_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if len(lines) == 0:
        raise ValueError("The prepared prompt is empty, so there is nothing to launch in T3 Code.")
    launch_t3_threads(workspace_root=workspace_root, requests=[T3ThreadRequest(title=lines[0][:T3_TITLE_MAX_CHARS], message=message)], target=target)
