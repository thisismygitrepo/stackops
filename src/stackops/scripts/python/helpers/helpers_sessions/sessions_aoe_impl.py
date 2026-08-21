"""Pure Python implementation for the sessions AoE run backend."""

import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig

type TabCommandMode = Literal["prompt", "cmd", "ignore"]


@dataclass(frozen=True, slots=True)
class AoeLaunchOptions:
    aoe_bin: str
    tool: str | None
    dry_run: bool
    sleep_inbetween: float
    tab_command_mode: TabCommandMode
    launch: bool


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
    tab: TabConfig,
    tab_command_mode: TabCommandMode,
) -> tuple[str | None, str | None]:
    tab_command = tab.get("command", "").strip()
    if tab_command_mode == "ignore" or tab_command == "":
        return None, None
    if tab_command_mode == "prompt":
        return tab_command, None
    return None, tab_command


def build_aoe_add_command(
    *,
    tab: TabConfig,
    title: str,
    group: str,
    options: AoeLaunchOptions,
) -> list[str]:
    prompt, command_override = _resolve_tab_payload(
        tab=tab,
        tab_command_mode=options.tab_command_mode,
    )

    command = [options.aoe_bin, "add", tab["startDir"]]
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
        raise ValueError("--sleep-inbetween must be >= 0.")
    if not options.dry_run and not _command_exists(options.aoe_bin):
        raise ValueError(
            f"Could not find AoE executable '{options.aoe_bin}'. "
            "Install agent-of-empires and make sure `aoe` is available on PATH."
        )

    pending_commands: list[tuple[str, str, list[str]]] = []
    used_titles: dict[str, int] = {}
    for layout in layouts_selected:
        group = layout["layoutName"]
        for tab_index, tab in enumerate(layout["layoutTabs"]):
            title = _resolve_unique_title(title=_default_title(tab=tab, tab_index=tab_index), used_titles=used_titles)
            pending_commands.append(
                (
                    group,
                    title,
                    build_aoe_add_command(tab=tab, title=title, group=group, options=options),
                )
            )

    if len(pending_commands) == 0:
        raise ValueError("No tabs were selected to launch through AoE.")

    for index, (group, title, command) in enumerate(pending_commands):
        printable = shlex.join(command)
        if options.dry_run:
            print(printable)
        else:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise ValueError(
                    f"aoe add failed for group '{group}' title '{title}'.\n"
                    f"Command: {printable}\n"
                    f"{detail or 'No error output returned.'}"
                )
            action = "Added and started" if options.launch else "Added"
            print(f"{action} AoE session '{title}' in group '{group}'.")
        if index < len(pending_commands) - 1 and options.sleep_inbetween > 0:
            time.sleep(options.sleep_inbetween)
