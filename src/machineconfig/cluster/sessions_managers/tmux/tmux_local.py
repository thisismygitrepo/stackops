#!/usr/bin/env python3
from pathlib import Path
import subprocess
from typing import TypedDict

from machineconfig.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
    SessionLaunchPlan,
    build_session_launch_plan,
    kill_existing_session,
)
from machineconfig.cluster.sessions_managers.session_exit_mode import SessionExitMode
from rich.console import Console

from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig
from machineconfig.cluster.sessions_managers.tmux.tmux_utils.tmux_helpers import (
    build_tmux_script,
    build_tmux_merge_script,
    check_tmux_session_status,
    build_unknown_command_status,
    validate_layout_config,
    TmuxSessionStatus,
)
from machineconfig.cluster.sessions_managers.zellij.zellij_utils.monitoring_types import CommandStatus


console = Console()
TMUX_MERGE_CONFLICT_ACTIONS = frozenset(
    {
        "mergeNewWindowsOverwriteMatchingWindows",
        "mergeNewWindowsSkipMatchingWindows",
    }
)


class TmuxLayoutSummary(TypedDict):
    total_commands: int
    running_commands: int
    stopped_commands: int
    session_healthy: bool


class TmuxLayoutStatus(TypedDict):
    tmux_session: TmuxSessionStatus
    commands: dict[str, CommandStatus]
    summary: TmuxLayoutSummary


class TmuxLayoutGenerator:
    def __init__(
        self,
        layout_config: LayoutConfig,
        session_name: str,
        exit_mode: SessionExitMode,
    ) -> None:
        self.session_name: str = session_name
        self.exit_mode: SessionExitMode = exit_mode
        self.layout_config: LayoutConfig = layout_config.copy()
        self.script_path: str | None = None

    def create_layout_file(self) -> bool:
        validate_layout_config(self.layout_config)
        tab_count = len(self.layout_config["layoutTabs"])
        layout_name = self.layout_config["layoutName"]
        console.print(f"[bold cyan]📋 Creating tmux layout[/bold cyan] [bright_green]'{layout_name}' with {tab_count} windows[/bright_green]")
        for tab in self.layout_config["layoutTabs"]:
            console.print(f"  [yellow]→[/yellow] [bold]{tab['tabName']}[/bold] [dim]in[/dim] [blue]{tab['startDir']}[/blue]")
        script_content = build_tmux_script(
            self.layout_config,
            self.session_name,
            self.exit_mode,
        )
        self._write_script_content(script_content=script_content)
        console.print(f"[bold green]✅ Layout created successfully:[/bold green] [cyan]{self.script_path}[/cyan]")
        return True

    def _write_script_content(self, script_content: str) -> None:
        tmp_dir = Path.home() / "tmp_results" / "sessions" / "tmux_layouts"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        if self.script_path is None:
            import tempfile

            layout_file = Path(tempfile.mkstemp(suffix="_layout.sh", dir=tmp_dir)[1])
        else:
            layout_file = Path(self.script_path)
        layout_file.write_text(script_content, encoding="utf-8")
        layout_file.chmod(layout_file.stat().st_mode | 0o111)
        self.script_path = str(layout_file.absolute())

    def check_all_commands_status(self) -> dict[str, CommandStatus]:
        if not self.layout_config:
            return {}
        status_report: dict[str, CommandStatus] = {}
        for tab in self.layout_config["layoutTabs"]:
            status_report[tab["tabName"]] = build_unknown_command_status(tab)
        return status_report

    def get_status_report(self) -> TmuxLayoutStatus:
        tmux_status = check_tmux_session_status(self.session_name or "default")
        commands_status = self.check_all_commands_status()
        running_count = sum(1 for status in commands_status.values() if status.get("running", False))
        total_count = len(commands_status)
        return {
            "tmux_session": tmux_status,
            "commands": commands_status,
            "summary": {
                "total_commands": total_count,
                "running_commands": running_count,
                "stopped_commands": total_count - running_count,
                "session_healthy": tmux_status.get("session_exists", False),
            },
        }

    def print_status_report(self) -> None:
        status = self.get_status_report()
        tmux_status = status["tmux_session"]
        commands = status["commands"]
        summary = status["summary"]
        console.print()
        console.print("[bold cyan]🔍 TMUX LAYOUT STATUS REPORT[/bold cyan]")
        if tmux_status.get("tmux_running", False):
            if tmux_status.get("session_exists", False):
                console.print(f"[bold green]✅ tmux session[/bold green] [yellow]'{self.session_name}'[/yellow] [green]is running[/green]")
            else:
                console.print(f"[bold yellow]⚠️  tmux is running but session[/bold yellow] [yellow]'{self.session_name}'[/yellow] [yellow]not found[/yellow]")
        else:
            console.print(f"[bold red]❌ tmux issue:[/bold red] [red]{tmux_status.get('error', 'Unknown error')}[/red]")
        console.print()
        for tab_name, cmd_status in commands.items():
            status_icon = "✅" if cmd_status.get("running", False) else "❌"
            cmd_text = cmd_status.get("command", "Unknown")
            if len(cmd_text) > 50:
                cmd_text = cmd_text[:47] + "..."
            console.print(f"   {status_icon} {tab_name}: {cmd_text}")
        console.print()
        console.print(
            f"[bold]Total commands:[/bold] {summary['total_commands']} | "
            f"[green]Running:[/green] {summary['running_commands']} | "
            f"[red]Stopped:[/red] {summary['stopped_commands']} | "
            f"[yellow]Session healthy:[/yellow] {'✅' if summary['session_healthy'] else '❌'}"
        )

    def prepare_launch_script(self, on_conflict: SessionConflictAction) -> None:
        session_status = check_tmux_session_status(self.session_name or "default")
        session_exists = session_status.get("session_exists", False)

        if session_exists and on_conflict in TMUX_MERGE_CONFLICT_ACTIONS:
            match on_conflict:
                case "mergeNewWindowsOverwriteMatchingWindows":
                    console.print(
                        f"[bold yellow]🔀 Merging tmux layout into existing session[/bold yellow] "
                        f"[yellow]'{self.session_name}'[/yellow] [yellow]and overwriting matching windows.[/yellow]"
                    )
                    script_content = build_tmux_merge_script(
                        layout_config=self.layout_config,
                        session_name=self.session_name,
                        on_conflict="mergeNewWindowsOverwriteMatchingWindows",
                        exit_mode=self.exit_mode,
                    )
                case "mergeNewWindowsSkipMatchingWindows":
                    console.print(
                        f"[bold yellow]🔀 Merging tmux layout into existing session[/bold yellow] "
                        f"[yellow]'{self.session_name}'[/yellow] [yellow]and skipping matching windows.[/yellow]"
                    )
                    script_content = build_tmux_merge_script(
                        layout_config=self.layout_config,
                        session_name=self.session_name,
                        on_conflict="mergeNewWindowsSkipMatchingWindows",
                        exit_mode=self.exit_mode,
                    )
                case _:
                    raise ValueError(f"Unsupported tmux merge policy: {on_conflict}")
        else:
            script_content = build_tmux_script(
                layout_config=self.layout_config,
                session_name=self.session_name,
                exit_mode=self.exit_mode,
            )

        self._write_script_content(script_content=script_content)

    def apply_launch_plan(
        self,
        launch_plan: SessionLaunchPlan,
        on_conflict: SessionConflictAction,
    ) -> None:
        if launch_plan["session_name"] != self.session_name:
            console.print(
                f"[bold yellow]📝 Renaming tmux session[/bold yellow] [yellow]'{self.session_name}'[/yellow] "
                f"[yellow]to[/yellow] [yellow]'{launch_plan['session_name']}'[/yellow] [yellow]to avoid session conflict.[/yellow]"
            )
            self.session_name = launch_plan["session_name"]
        if launch_plan["restart_required"]:
            console.print(
                f"[bold yellow]♻️ Restarting existing tmux session[/bold yellow] [yellow]'{self.session_name}'[/yellow]"
            )
            kill_existing_session("tmux", self.session_name)
        self.prepare_launch_script(on_conflict=on_conflict)

    def run(self, on_conflict: SessionConflictAction) -> dict[str, str | int]:
        launch_plan = build_session_launch_plan([self.session_name], backend="tmux", on_conflict=on_conflict)[0]
        self.apply_launch_plan(
            launch_plan=launch_plan,
            on_conflict=on_conflict,
        )
        if self.script_path is None:
            raise RuntimeError("Script path was not set after creating layout file")
        result = subprocess.run(["bash", self.script_path], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to run tmux layout: {result.stderr or result.stdout}")
        return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def run_tmux_layout(layout_config: LayoutConfig, on_conflict: SessionConflictAction) -> None:
    session_name = layout_config["layoutName"]
    generator = TmuxLayoutGenerator(
        layout_config=layout_config,
        session_name=session_name,
        exit_mode="backToShell",
    )
    generator.create_layout_file()
    generator.run(on_conflict=on_conflict)


if __name__ == "__main__":
    sample_layout: LayoutConfig = {
        "layoutName": "sample_layout",
        "layoutTabs": [
            {"tabName": "editor", "startDir": "~/projects", "command": "nvim"},
            {"tabName": "server", "startDir": "~/projects/server", "command": "yazi"},
            {"tabName": "logs", "startDir": "~/projects/server/logs", "command": "tail -f server.log"},
        ],
    }
    run_tmux_layout(sample_layout, on_conflict="error")
