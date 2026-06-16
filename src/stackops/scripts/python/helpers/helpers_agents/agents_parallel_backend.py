"""Backend helpers for launching generated parallel agent layouts."""

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_layouts import read_generated_layouts
from stackops.utils.schemas.layouts.layout_types import TabConfig


AgentParallelBackend: TypeAlias = Literal["tmux", "herdr", "aoe"]
AgentParallelBackendOption: TypeAlias = Literal["tmux", "t", "herdr", "h", "aoe", "e"]
DEFAULT_AGENT_PARALLEL_BACKEND: Final[AgentParallelBackend] = "tmux"
AGENT_PARALLEL_BACKENDS: Final[tuple[AgentParallelBackend, ...]] = ("tmux", "herdr", "aoe")
AGENT_PARALLEL_BACKEND_HELP: Final[str] = "tmux, herdr, or aoe"

JsonObject: TypeAlias = dict[str, object]


@dataclass(frozen=True, slots=True)
class HerdrLaunchedTab:
    name: str
    tab_id: str
    pane_id: str


@dataclass(frozen=True, slots=True)
class HerdrLaunchSummary:
    workspace_id: str
    workspace_label: str
    tabs: tuple[HerdrLaunchedTab, ...]


def resolve_agent_parallel_backend(backend: AgentParallelBackendOption | AgentParallelBackend) -> AgentParallelBackend:
    match backend:
        case "tmux" | "t":
            return "tmux"
        case "herdr" | "h":
            return "herdr"
        case "aoe" | "e":
            return "aoe"
        case _:
            raise ValueError(f"Unsupported backend '{backend}'. Use {AGENT_PARALLEL_BACKEND_HELP}.")


def run_generated_layout(*, layout_output_path: Path, backend: AgentParallelBackend, agent: str | None = None) -> None:
    match backend:
        case "tmux":
            _run_generated_layout_with_tmux(layout_output_path=layout_output_path)
        case "herdr":
            summary = run_generated_layout_with_herdr(layout_output_path=layout_output_path)
            _show_herdr_launch_summary(summary=summary)
        case "aoe":
            from stackops.scripts.python.helpers.helpers_agents.agents_parallel_aoe_backend import run_generated_layout_with_aoe

            run_generated_layout_with_aoe(layout_output_path=layout_output_path, agent=agent)
        case _:
            raise ValueError(f"Unsupported backend '{backend}'. Use {AGENT_PARALLEL_BACKEND_HELP}.")


def run_generated_layout_with_herdr(*, layout_output_path: Path) -> HerdrLaunchSummary:
    layouts = read_generated_layouts(layout_output_path=layout_output_path)
    if len(layouts) != 1:
        raise RuntimeError(f"Herdr backend expects one generated layout, found {len(layouts)} in {layout_output_path}")
    layout = layouts[0]
    tabs = layout["layoutTabs"]
    if len(tabs) == 0:
        raise RuntimeError(f"Herdr backend cannot launch layout '{layout['layoutName']}' because it has no tabs.")

    first_tab = tabs[0]
    workspace_payload = _run_herdr_json(
        ["herdr", "workspace", "create", "--cwd", first_tab["startDir"], "--label", layout["layoutName"], "--no-focus"]
    )
    workspace = _result_object(payload=workspace_payload, key="workspace")
    root_pane = _result_object(payload=workspace_payload, key="root_pane")
    root_tab = _result_object(payload=workspace_payload, key="tab")
    workspace_id = _required_string(mapping=workspace, key="workspace_id")
    root_tab_id = _required_string(mapping=root_tab, key="tab_id")
    root_pane_id = _required_string(mapping=root_pane, key="pane_id")

    launched_tabs: list[HerdrLaunchedTab] = []
    _run_herdr(["herdr", "tab", "rename", root_tab_id, first_tab["tabName"]])
    _run_tab_command(tab=first_tab, pane_id=root_pane_id)
    launched_tabs.append(HerdrLaunchedTab(name=first_tab["tabName"], tab_id=root_tab_id, pane_id=root_pane_id))

    for tab in tabs[1:]:
        tab_payload = _run_herdr_json(
            ["herdr", "tab", "create", "--workspace", workspace_id, "--cwd", tab["startDir"], "--label", tab["tabName"], "--no-focus"]
        )
        created_tab = _result_object(payload=tab_payload, key="tab")
        created_pane = _result_object(payload=tab_payload, key="root_pane")
        tab_id = _required_string(mapping=created_tab, key="tab_id")
        pane_id = _required_string(mapping=created_pane, key="pane_id")
        _run_tab_command(tab=tab, pane_id=pane_id)
        launched_tabs.append(HerdrLaunchedTab(name=tab["tabName"], tab_id=tab_id, pane_id=pane_id))

    return HerdrLaunchSummary(workspace_id=workspace_id, workspace_label=layout["layoutName"], tabs=tuple(launched_tabs))


def _run_tab_command(*, tab: TabConfig, pane_id: str) -> None:
    _run_herdr(["herdr", "pane", "run", pane_id, tab["command"]])


def _run_generated_layout_with_tmux(*, layout_output_path: Path) -> None:
    from stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run import run_cli

    run_cli(
        ctx=None,
        layouts_file=str(layout_output_path),
        test_layout=False,
        choose_layouts=None,
        choose_tabs=None,
        sleep_inbetween=1.0,
        max_tabs=100,
        max_layouts=25,
        monitor=False,
        parallel_layouts=None,
        backend="tmux",
        on_conflict="restart",
        exit_mode="backToShell",
        kill_upon_completion=False,
        subsitute_home=False,
    )


def _run_herdr(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, check=False, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("Herdr backend requested, but `herdr` was not found in PATH.") from exc
    if result.returncode == 0:
        return result.stdout
    detail = (result.stderr or result.stdout or "unknown error").strip()
    raise RuntimeError(f"Herdr command failed ({shlex.join(args)}): {detail}")


def _run_herdr_json(args: list[str]) -> JsonObject:
    stdout = _run_herdr(args).strip()
    if stdout == "":
        raise RuntimeError(f"Herdr command did not return JSON: {shlex.join(args)}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Herdr command returned invalid JSON ({shlex.join(args)}): {stdout}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Herdr command returned non-object JSON ({shlex.join(args)}): {stdout}")
    return cast(JsonObject, payload)


def _result_object(*, payload: JsonObject, key: str) -> JsonObject:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Herdr JSON response did not include an object result.")
    value = result.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"Herdr JSON response did not include result.{key}.")
    return cast(JsonObject, value)


def _required_string(*, mapping: JsonObject, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _show_herdr_launch_summary(*, summary: HerdrLaunchSummary) -> None:
    typer.echo(f"Started Herdr workspace '{summary.workspace_label}' ({summary.workspace_id}) with {len(summary.tabs)} agent tab(s).")
    for tab in summary.tabs:
        typer.echo(f"- {tab.name}: tab={tab.tab_id} pane={tab.pane_id}")
