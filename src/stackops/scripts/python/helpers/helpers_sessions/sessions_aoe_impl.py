"""Pure Python implementation for the sessions AoE run backend."""

import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.console import Console

from stackops.cluster.sessions_managers.session_launch_table import LaunchedPaneRow, print_launch_table
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabConfig, resolve_start_dir

type TabCommandMode = Literal["prompt", "cmd", "ignore"]


@dataclass(frozen=True, slots=True)
class AoeLaunchOptions:
    aoe_bin: str
    tool: str | None
    dry_run: bool
    sleep_inbetween: float
    tab_command_mode: TabCommandMode
    launch: bool


@dataclass(frozen=True, slots=True)
class _PendingAoeSession:
    group: str
    title: str
    tab_name: str
    pane: PaneConfig
    command: list[str]


def _command_exists(command: str) -> bool:
    if shutil.which(command) is not None:
        return True
    return Path(command).expanduser().exists()


def _default_title(tab: TabConfig, tab_index: int) -> str:
    title = tab.get("tabName", "").strip()
    if title:
        return title
    return f"tab{tab_index + 1}"


def _resolve_unique_title(title: str, used_titles: dict[str, int]) -> str:
    seen = used_titles.get(title, 0)
    used_titles[title] = seen + 1
    if seen == 0:
        return title
    return f"{title}_{seen + 1}"


def _resolve_tab_payload(
    pane: PaneConfig,
    tab_command_mode: TabCommandMode,
) -> tuple[str | None, str | None]:
    tab_command = pane["command"].strip()
    if tab_command_mode == "ignore" or tab_command == "":
        return None, None
    if tab_command_mode == "prompt":
        return tab_command, None
    return None, tab_command


def _launched_row(session: _PendingAoeSession, options: AoeLaunchOptions) -> LaunchedPaneRow:
    prompt, command_override = _resolve_tab_payload(pane=session.pane, tab_command_mode=options.tab_command_mode)
    match prompt, command_override:
        case str(), _:
            command = f"""prompt: {prompt}"""
        case None, str():
            command = command_override
        case None, None:
            command = "—"
    return LaunchedPaneRow(
        location=options.tool or "default",
        tab_name=session.tab_name,
        pane_name=session.pane["paneName"],
        handle=session.title,
        command=command,
        start_dir=session.pane["startDir"],
    )


def build_aoe_add_command(
    *,
    pane: PaneConfig,
    title: str,
    group: str,
    options: AoeLaunchOptions,
) -> list[str]:
    prompt, command_override = _resolve_tab_payload(
        pane=pane,
        tab_command_mode=options.tab_command_mode,
    )

    command = [options.aoe_bin, "add", resolve_start_dir(pane["startDir"])]
    command.extend(["--title", title])
    command.extend(["--group", group])

    if options.tool is not None:
        command.extend(["--tool", options.tool])
    if command_override is not None:
        command.extend(["--cmd-override", command_override])
    if prompt is not None:
        command.extend(["--extra-args", shlex.join([prompt])])
    if options.launch:
        command.append("--launch")

    return command


def run_layouts_via_aoe(layouts_selected: list[LayoutConfig], options: AoeLaunchOptions) -> None:
    if options.sleep_inbetween < 0:
        raise ValueError("--launch-delay must be >= 0.")
    if not options.dry_run and not _command_exists(options.aoe_bin):
        raise ValueError(
            f"Could not find AoE executable '{options.aoe_bin}'. "
            "Install agent-of-empires and make sure `aoe` is available on PATH."
        )

    pending_sessions: list[_PendingAoeSession] = []
    used_titles: dict[str, int] = {}
    for layout in layouts_selected:
        group = layout["layoutName"]
        for tab_index, tab in enumerate(layout["layoutTabs"]):
            if len(tab["panes"]) != 1:
                raise ValueError(
                    f"AoE starts one agent session per tab, but tab '{tab['tabName']}' in layout '{group}' "
                    f"has {len(tab['panes'])} panes. Use the tmux, herdr or tuios backend for multi-pane tabs."
                )
            title = _resolve_unique_title(title=_default_title(tab=tab, tab_index=tab_index), used_titles=used_titles)
            pane = tab["panes"][0]
            pending_sessions.append(
                _PendingAoeSession(
                    group=group,
                    title=title,
                    tab_name=tab["tabName"],
                    pane=pane,
                    command=build_aoe_add_command(pane=pane, title=title, group=group, options=options),
                )
            )

    if len(pending_sessions) == 0:
        raise ValueError("No tabs were selected to launch through AoE.")

    if options.dry_run:
        for index, session in enumerate(pending_sessions):
            print(shlex.join(session.command))
            if index < len(pending_sessions) - 1 and options.sleep_inbetween > 0:
                time.sleep(options.sleep_inbetween)
        return

    launched_sessions: list[_PendingAoeSession] = []
    try:
        with Console().status("Launching AoE sessions…") as status:
            for index, session in enumerate(pending_sessions):
                status.update(f"""Launching AoE session '{session.title}' ({index + 1}/{len(pending_sessions)})…""")
                result = subprocess.run(session.command, capture_output=True, text=True, timeout=120, check=False)
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout).strip()
                    raise ValueError(
                        f"aoe add failed for group '{session.group}' title '{session.title}'.\n"
                        f"Command: {shlex.join(session.command)}\n"
                        f"{detail or 'No error output returned.'}"
                    )
                launched_sessions.append(session)
                if index < len(pending_sessions) - 1 and options.sleep_inbetween > 0:
                    time.sleep(options.sleep_inbetween)
    finally:
        for group in dict.fromkeys(session.group for session in launched_sessions):
            print_launch_table(
                backend="aoe",
                session_name=group,
                rows=[_launched_row(session=session, options=options) for session in launched_sessions if session.group == group],
                verb="started" if options.launch else "added",
            )
