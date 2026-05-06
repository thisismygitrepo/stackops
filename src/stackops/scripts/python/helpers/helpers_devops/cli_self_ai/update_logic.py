from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.graph.generate_cli_graph import build_cli_graph
from stackops.scripts.python.helpers.helpers_agents.agents_impl import agents_create as agents_create_impl
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_SEAPRATOR, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


DEFAULT_LOGIC_JOB_NAME = "updateLogic"
UPDATE_LOGIC_PROMPT = """
Please check the logic of the command below, and fix if you found anything not tight, inconsistent, fail mode etc.
If code is okay for reasonable use cases, just leave it without change, you don't have to be very fussy. I dont want unnecessary complexity.
"""

type JsonObject = dict[str, object]


@dataclass(frozen=True, slots=True)
class CommandLogicContextEntry:
    source_file: str
    command_name: str

    def render(self) -> str:
        return f"file: {self.source_file}\ncommand: {self.command_name}"


def get_developer_repo_root() -> Path:
    return Path.home().joinpath("code", "stackops")


def _as_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(key, str) for key in value):
        return None
    return value


def _as_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _collect_command_context_entries(*, node: JsonObject) -> tuple[CommandLogicContextEntry, ...]:
    collected_entries: list[CommandLogicContextEntry] = []

    if _as_string(node.get("kind")) == "command":
        source = _as_json_object(node.get("source"))
        if source is None:
            raise ValueError("Command entry is missing source metadata")

        source_file = _as_string(source.get("file")).strip()
        command_name = _as_string(node.get("fullPath")).strip()
        if source_file == "" or command_name == "":
            raise ValueError("Command entry must define both source.file and fullPath")
        collected_entries.append(CommandLogicContextEntry(source_file=source_file, command_name=command_name))

    children = node.get("children")
    if children is None:
        return tuple(collected_entries)
    if not isinstance(children, list):
        raise ValueError("CLI graph node children must be a list when defined")

    for child in children:
        child_node = _as_json_object(child)
        if child_node is None:
            raise ValueError("CLI graph contains a non-object child node")
        collected_entries.extend(_collect_command_context_entries(node=child_node))
    return tuple(collected_entries)


def build_logic_context_from_graph(*, graph_payload: JsonObject) -> str:
    root = _as_json_object(graph_payload.get("root"))
    if root is None:
        raise ValueError("CLI graph payload is missing a root object")

    command_entries = sorted(
        _collect_command_context_entries(node=root),
        key=lambda entry: (entry.source_file, entry.command_name),
    )
    if len(command_entries) == 0:
        raise ValueError("CLI graph does not define any command entries")
    return DEFAULT_SEAPRATOR.join(entry.render() for entry in command_entries)


def _resolve_prompt(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> str | None:
    if prompt is not None:
        return prompt
    if prompt_path is not None or prompt_name is not None:
        return None
    return UPDATE_LOGIC_PROMPT


def _resolve_prompt_path(*, prompt: str | None, prompt_path: str | None, prompt_name: str | None) -> str | None:
    if prompt is not None or prompt_name is not None:
        return None
    return prompt_path


def update_logic(
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent type.")] = "codex",
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use, agent will use its default otherwise.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(
            "--reasoning",
            "-r",
            help="Reasoning effort for codex, copilot, and pi agents. Unsupported agents ignore it and use their default.",
        ),
    ] = None,
    provider: Annotated[PROVIDER | None, typer.Option("--provider", "-v", help="Provider to use (if the agent supports many).")] = None,
    host: Annotated[HOST, typer.Option("--host", "-h", help="Machine to run agents on.")] = "local",
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", min=1, help="Number of tasks per prompt.")] = 10,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Prompt prefix as string.")] = None,
    prompt_path: Annotated[
        str | None,
        typer.Option(
            "--prompt-path",
            "-P",
            help="Prompt file path. When omitted, update-logic uses its embedded default prompt unless --prompt or --prompt-name is provided.",
        ),
    ] = None,
    prompt_name: Annotated[str | None, typer.Option("--prompt-name", "-N", help="Prompt entry name from prompts YAML.")] = None,
    job_name: Annotated[str, typer.Option("--job-name", "-n", help="Job label and default output directory stem.")] = DEFAULT_LOGIC_JOB_NAME,
    join_prompt_and_context: Annotated[
        bool,
        typer.Option("--joined-prompt-context", "-j", help="Join prompt file to the context."),
    ] = False,
    output_path: Annotated[
        str | None,
        typer.Option("--output-path", "-o", help="Layout path. Defaults to <agents-dir>/layout.json."),
    ] = None,
    agents_dir: Annotated[
        str | None,
        typer.Option("--agents-dir", "-d", help="Agent work directory. Defaults to $HOME/code/stackops/.ai/agents/<job-name>."),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Whether to run in interactive mode, asking for missing parameters."),
    ] = False,
) -> None:
    repo_root = get_developer_repo_root()
    if not repo_root.joinpath("pyproject.toml").is_file():
        raise RuntimeError(f"Developer repo not found: {repo_root}")

    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else repo_root.joinpath(".ai", "agents", job_name)
    resolved_output_path = Path(output_path) if output_path is not None else resolved_agents_dir.joinpath("layout.json")
    context_content = build_logic_context_from_graph(graph_payload=build_cli_graph())
    context_output_path = resolved_agents_dir.joinpath("context.md")

    try:
        agents_create_impl(
            agent=agent,
            model=model,
            agent_load=agent_load,
            context=context_content,
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            prompt=_resolve_prompt(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name),
            prompt_path=_resolve_prompt_path(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name),
            prompt_name=prompt_name,
            job_name=job_name,
            join_prompt_and_context=join_prompt_and_context,
            output_path=str(resolved_output_path),
            agents_dir=str(resolved_agents_dir),
            host=host,
            reasoning_effort=reasoning_effort,
            provider=provider,
            interactive=interactive,
        )
    finally:
        context_output_path.parent.mkdir(parents=True, exist_ok=True)
        context_output_path.write_text(context_content, encoding="utf-8")
