"""Pure Python implementations for sessions run-aoe command."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig

TabCommandMode = Literal["prompt", "cmd", "ignore"]
AoeAddStyle = Literal["legacy", "modern"]


@dataclass(frozen=True)
class AoeLaunchOptions:
    aoe_bin: str
    agent: Optional[str]
    model: Optional[str]
    provider: Optional[str]
    sandbox: Optional[str]
    yolo: bool
    cmd: Optional[str]
    extra_agent_args: tuple[str, ...]
    env_vars: tuple[str, ...]
    force: bool
    dry_run: bool
    sleep_inbetween: float
    tab_command_mode: TabCommandMode


@dataclass(frozen=True)
class AoeAddInterface:
    style: AoeAddStyle


def _command_exists(command: str) -> bool:
    if shutil.which(command) is not None:
        return True
    return Path(command).expanduser().exists()


def _validate_env_vars(env_vars: tuple[str, ...]) -> None:
    for item in env_vars:
        if "=" not in item:
            raise ValueError(f"Invalid --env value '{item}'. Expected KEY=VALUE.")
        key, _ = item.split("=", 1)
        if key.strip() == "":
            raise ValueError(f"Invalid --env value '{item}'. Environment variable key cannot be empty.")


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
    options: AoeLaunchOptions,
) -> tuple[Optional[str], Optional[str]]:
    tab_command = tab.get("command", "").strip()
    if options.tab_command_mode == "ignore" or tab_command == "":
        return None, options.cmd
    if options.tab_command_mode == "prompt":
        return tab_command, options.cmd
    if options.cmd is not None:
        raise ValueError("--cmd cannot be combined with --tab-command-mode cmd.")
    return None, tab_command


def _resolved_extra_args(options: AoeLaunchOptions) -> list[str]:
    result = list(options.extra_agent_args)
    if options.sandbox is not None:
        result.extend(["--sandbox", options.sandbox])
    if options.yolo:
        result.append("--yolo")
    return result


def _inspect_aoe_add_interface(aoe_bin: str) -> AoeAddInterface:
    result = subprocess.run([aoe_bin, "add", "--help"], capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(
            f"Could not inspect AoE CLI via `{aoe_bin} add --help`.\n"
            f"{detail or 'No error output returned.'}"
        )

    help_text = f"{result.stdout}\n{result.stderr}"
    if "--cmd-override" in help_text or "--extra-args" in help_text:
        return AoeAddInterface(style="modern")
    return AoeAddInterface(style="legacy")


def _resolved_modern_extra_args(
    *,
    prompt: Optional[str],
    options: AoeLaunchOptions,
) -> list[str]:
    result: list[str] = []

    if options.model is not None:
        result.extend(["--model", options.model])

    if options.provider is not None:
        if options.agent not in (None, "codex"):
            raise ValueError(
                "Current AoE CLI no longer exposes `aoe add --provider`. "
                "`--provider` can only be auto-mapped for codex sessions."
            )
        result.extend(["--config", f'model_provider="{options.provider}"'])

    if options.sandbox is not None:
        result.extend(["--sandbox", options.sandbox])

    result.extend(options.extra_agent_args)

    # Codex accepts an optional positional prompt, so keep it last.
    if prompt is not None:
        result.append(prompt)

    return result


def _build_legacy_aoe_add_command(
    *,
    tab: TabConfig,
    title: str,
    group: str,
    options: AoeLaunchOptions,
) -> list[str]:
    prompt, command_override = _resolve_tab_payload(tab=tab, options=options)

    command = [options.aoe_bin, "add", tab["startDir"]]
    command.extend(["--title", title])
    command.extend(["--group", group])

    if options.agent is not None:
        command.extend(["--agent", options.agent])
    if options.model is not None:
        command.extend(["--model", options.model])
    if options.provider is not None:
        command.extend(["--provider", options.provider])
    if prompt is not None:
        command.extend(["--prompt", prompt])
    if command_override is not None:
        command.extend(["--cmd", command_override])

    for extra_arg in _resolved_extra_args(options=options):
        command.extend(["--args", extra_arg])
    for env_var in options.env_vars:
        command.extend(["--env", env_var])
    if options.force:
        command.append("--force")

    return command


def _build_modern_aoe_add_command(
    *,
    tab: TabConfig,
    title: str,
    group: str,
    options: AoeLaunchOptions,
) -> list[str]:
    prompt, command_override = _resolve_tab_payload(tab=tab, options=options)

    if options.env_vars:
        raise ValueError(
            "Current AoE CLI does not support `aoe add --env`. "
            "Remove `--env` or use an older AoE version."
        )
    if options.force:
        raise ValueError(
            "Current AoE CLI does not support `aoe add --force`. "
            "Remove `--force` or use an older AoE version."
        )

    command = [options.aoe_bin, "add", tab["startDir"]]
    command.extend(["--title", title])
    command.extend(["--group", group])

    if options.agent is not None:
        command.extend(["--cmd", options.agent])
    if options.yolo:
        command.append("--yolo")
    if command_override is not None:
        command.extend(["--cmd-override", command_override])

    extra_args = _resolved_modern_extra_args(prompt=prompt, options=options)
    if extra_args:
        command.extend(["--extra-args", shlex.join(extra_args)])

    return command


def build_aoe_add_command(
    *,
    tab: TabConfig,
    title: str,
    group: str,
    options: AoeLaunchOptions,
    interface: AoeAddInterface,
) -> list[str]:
    if interface.style == "modern":
        return _build_modern_aoe_add_command(tab=tab, title=title, group=group, options=options)
    return _build_legacy_aoe_add_command(tab=tab, title=title, group=group, options=options)


def run_layouts_via_aoe(layouts_selected: list[LayoutConfig], options: AoeLaunchOptions) -> None:
    if options.sleep_inbetween < 0:
        raise ValueError("--sleep-inbetween must be >= 0.")
    if not options.dry_run and not _command_exists(options.aoe_bin):
        raise ValueError(
            f"Could not find AoE executable '{options.aoe_bin}'. "
            "Install agent-of-empires or pass --aoe-bin with an explicit path."
        )

    _validate_env_vars(options.env_vars)
    interface = _inspect_aoe_add_interface(options.aoe_bin) if _command_exists(options.aoe_bin) else AoeAddInterface(style="legacy")

    pending_commands: list[tuple[str, str, list[str]]] = []
    for layout in layouts_selected:
        group = layout["layoutName"]
        used_titles: dict[str, int] = {}
        for tab_index, tab in enumerate(layout["layoutTabs"]):
            title = _resolve_unique_title(title=_default_title(tab=tab, tab_index=tab_index), used_titles=used_titles)
            pending_commands.append(
                (
                    group,
                    title,
                    build_aoe_add_command(tab=tab, title=title, group=group, options=options, interface=interface),
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
            print(f"Added AoE session '{title}' in group '{group}'.")
        if index < len(pending_commands) - 1 and options.sleep_inbetween > 0:
            time.sleep(options.sleep_inbetween)
