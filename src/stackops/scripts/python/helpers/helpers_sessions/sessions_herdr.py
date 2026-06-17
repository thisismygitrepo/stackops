"""Herdr layout launcher for terminal run."""

import json
import shlex
import subprocess
from dataclasses import dataclass
from typing import TypeAlias, cast

import typer

from stackops.cluster.sessions_managers.monitoring_types import StartResult
from stackops.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
    build_session_launch_plan,
    kill_existing_session,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


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


def run_layouts_with_herdr(
    *,
    layouts_selected: list[LayoutConfig],
    on_conflict: SessionConflictAction,
) -> dict[str, StartResult]:
    results: dict[str, StartResult] = {}
    launch_plan = build_session_launch_plan(
        requested_session_names=[layout["layoutName"] for layout in layouts_selected],
        backend="herdr",
        on_conflict=on_conflict,
    )
    for layout, plan in zip(layouts_selected, launch_plan, strict=True):
        original_workspace_label = layout["layoutName"]
        workspace_label = original_workspace_label
        if plan.get("skip_launch", False):
            results[workspace_label] = {
                "success": True,
                "message": f"Skipped existing Herdr workspace '{workspace_label}'",
            }
            continue
        if plan["session_name"] != workspace_label:
            typer.echo(
                f"Renaming Herdr workspace '{workspace_label}' to "
                f"'{plan['session_name']}' to avoid workspace conflict."
            )
            workspace_label = plan["session_name"]
            layout = {
                "layoutName": workspace_label,
                "layoutTabs": layout["layoutTabs"],
            }
        if plan["restart_required"]:
            typer.echo(f"Restarting existing Herdr workspace '{workspace_label}'.")
            kill_existing_session("herdr", workspace_label)
        try:
            summary = launch_layout_with_herdr(layout=layout)
        except Exception as exc:
            results[workspace_label] = {"success": False, "error": str(exc)}
            continue
        results[workspace_label] = {
            "success": True,
            "message": (
                f"Started Herdr workspace '{summary.workspace_label}' "
                f"({summary.workspace_id}) with {len(summary.tabs)} tab(s)"
            ),
        }
        show_herdr_launch_summary(summary=summary)
    return results


def launch_layout_with_herdr(*, layout: LayoutConfig) -> HerdrLaunchSummary:
    tabs = layout["layoutTabs"]
    if len(tabs) == 0:
        raise RuntimeError(
            f"Herdr backend cannot launch layout '{layout['layoutName']}' "
            "because it has no tabs."
        )

    first_tab = tabs[0]
    workspace_payload = _run_herdr_json(
        [
            "herdr",
            "workspace",
            "create",
            "--cwd",
            first_tab["startDir"],
            "--label",
            layout["layoutName"],
            "--no-focus",
        ]
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
    launched_tabs.append(
        HerdrLaunchedTab(
            name=first_tab["tabName"],
            tab_id=root_tab_id,
            pane_id=root_pane_id,
        )
    )

    for tab in tabs[1:]:
        tab_payload = _run_herdr_json(
            [
                "herdr",
                "tab",
                "create",
                "--workspace",
                workspace_id,
                "--cwd",
                tab["startDir"],
                "--label",
                tab["tabName"],
                "--no-focus",
            ]
        )
        created_tab = _result_object(payload=tab_payload, key="tab")
        created_pane = _result_object(payload=tab_payload, key="root_pane")
        tab_id = _required_string(mapping=created_tab, key="tab_id")
        pane_id = _required_string(mapping=created_pane, key="pane_id")
        _run_tab_command(tab=tab, pane_id=pane_id)
        launched_tabs.append(
            HerdrLaunchedTab(
                name=tab["tabName"],
                tab_id=tab_id,
                pane_id=pane_id,
            )
        )

    return HerdrLaunchSummary(
        workspace_id=workspace_id,
        workspace_label=layout["layoutName"],
        tabs=tuple(launched_tabs),
    )


def _run_tab_command(*, tab: TabConfig, pane_id: str) -> None:
    _run_herdr(["herdr", "pane", "run", pane_id, tab["command"]])


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
        raise RuntimeError(
            f"Herdr command returned invalid JSON ({shlex.join(args)}): {stdout}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Herdr command returned non-object JSON ({shlex.join(args)}): {stdout}"
        )
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


def show_herdr_launch_summary(*, summary: HerdrLaunchSummary) -> None:
    typer.echo(
        f"Started Herdr workspace '{summary.workspace_label}' "
        f"({summary.workspace_id}) with {len(summary.tabs)} tab(s)."
    )
    for tab in summary.tabs:
        typer.echo(f"- {tab.name}: tab={tab.tab_id} pane={tab.pane_id}")
