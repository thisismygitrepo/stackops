import shlex
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux import build_mount_pane_command, build_tmux_launch_command


@dataclass(frozen=True)
class TmuxServer:
    directory: Path
    environment: dict[str, str]


@dataclass(frozen=True)
class Pane:
    identifier: str
    active: bool


def _run_tmux(server: TmuxServer, arguments: list[str]) -> str:
    result = subprocess.run(
        ["tmux", *arguments], cwd=server.directory, env=server.environment, capture_output=True, text=True, timeout=10, check=True
    )
    return result.stdout.strip()


def _read_panes(server: TmuxServer, target: str) -> tuple[Pane, ...]:
    output = _run_tmux(server=server, arguments=["list-panes", "-t", target, "-F", "#{pane_id}|#{pane_active}"])
    panes: list[Pane] = []
    for line in output.splitlines():
        identifier, active = line.split("|")
        panes.append(Pane(identifier=identifier, active=active == "1"))
    return tuple(panes)


@pytest.fixture
def isolated_tmux_server() -> Iterator[TmuxServer]:
    tmux_binary = shutil.which("tmux")
    if tmux_binary is None:
        pytest.skip("tmux is required for cloud mount integration tests")
    temporary_root = Path(__file__).resolve().parents[8] / ".ai" / "tmp_scripts" / "cloud_mount_regression"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="case-", dir=temporary_root) as directory_name:
        directory = Path(directory_name)
        binary_directory = directory / "bin"
        binary_directory.mkdir()
        configuration = directory / "tmux.conf"
        configuration.write_text(
            """set -g default-shell /bin/sh
set -g default-command /bin/sh
set -g default-size 80x24
set -g automatic-rename off
""",
            encoding="utf-8",
        )
        tmux_wrapper = binary_directory / "tmux"
        tmux_wrapper.write_text(
            f"""#!/bin/sh
case "$1" in attach|switch-client) exit 0 ;; esac
exec {shlex.quote(tmux_binary)} -S {shlex.quote(str(directory / "tmux.sock"))} -f {shlex.quote(str(configuration))} "$@"
""",
            encoding="utf-8",
        )
        tmux_wrapper.chmod(0o700)
        bash_stub = binary_directory / "bash"
        bash_stub.write_text(
            """#!/bin/sh
printf '%s' "$2" > "$HOME/$TMUX_PANE.command"
tmux wait-for -S "$TMUX_PANE-ready"
exec /bin/sleep 600
""",
            encoding="utf-8",
        )
        bash_stub.chmod(0o700)
        server = TmuxServer(
            directory=directory,
            environment={"PATH": f"""{binary_directory}:/usr/bin:/bin""", "HOME": directory_name, "SHELL": "/bin/sh", "TERM": "xterm-256color"},
        )
        _run_tmux(server=server, arguments=["new-session", "-d", "-s", "fixture", "-n", "fixture"])
        try:
            yield server
        finally:
            _run_tmux(server=server, arguments=["kill-server"])


@pytest.mark.parametrize("base_index", [0, 1])
@pytest.mark.parametrize("session_exists", [False, True])
def test_mount_windows_use_actual_panes_and_preserve_existing_windows(
    isolated_tmux_server: TmuxServer, base_index: int, session_exists: bool
) -> None:
    server = isolated_tmux_server
    _run_tmux(server=server, arguments=["set-option", "-g", "base-index", str(base_index)])
    _run_tmux(server=server, arguments=["set-window-option", "-g", "pane-base-index", str(base_index)])
    if session_exists:
        _run_tmux(server=server, arguments=["new-session", "-d", "-s", "cloud mount", "-n", "existing"])
    locations = {remote: str(server.directory / f"""mount {remote}""") for remote in ("odOracle", "shpo", "odo")}
    mount_commands = {remote: f"""rclone mount {remote}: {shlex.quote(location)}""" for remote, location in locations.items()}
    script = build_tmux_launch_command(mount_commands=mount_commands, mount_locations=locations, session_name="cloud mount", unmounted_clouds=set())

    result = subprocess.run(
        ["/bin/sh", "-c", script], cwd=server.directory, env=server.environment, capture_output=True, text=True, timeout=10, check=False
    )

    assert result.returncode == 0, result.stderr
    original_panes: dict[str, tuple[Pane, ...]] = {}
    for remote, location in locations.items():
        panes = _read_panes(server=server, target=f"""=cloud mount:={remote}""")
        original_panes[remote] = panes
        assert len(panes) == 5
        commands: dict[str, str] = {}
        for pane in panes:
            _run_tmux(server=server, arguments=["wait-for", f"""{pane.identifier}-ready"""])
            commands[pane.identifier] = (server.directory / f"""{pane.identifier}.command""").read_text(encoding="utf-8")
        assert set(commands.values()) == {
            shlex.split(build_mount_pane_command(mount_command=mount_commands[remote]))[2],
            f"""rclone about {remote}:; exec bash""",
            f"""yazi {shlex.quote(location)}""",
            "btm --default_widget_type net --expanded",
            f"""cd {shlex.quote(location)}; exec bash""",
        }
        active_panes = [pane for pane in panes if pane.active]
        assert len(active_panes) == 1
        assert commands[active_panes[0].identifier] == f"""cd {shlex.quote(location)}; exec bash"""
    assert _run_tmux(server=server, arguments=["display-message", "-p", "-t", "=cloud mount:", "#{window_name}"]) == "odOracle"

    repeated_result = subprocess.run(
        ["/bin/sh", "-c", script], cwd=server.directory, env=server.environment, capture_output=True, text=True, timeout=10, check=False
    )

    assert repeated_result.returncode == 0, repeated_result.stderr
    for remote, panes in original_panes.items():
        assert _read_panes(server=server, target=f"""=cloud mount:={remote}""") == panes
    window_names = _run_tmux(server=server, arguments=["list-windows", "-t", "=cloud mount", "-F", "#{window_name}"]).splitlines()
    assert set(window_names) == set(locations) | ({"existing"} if session_exists else set())


@pytest.mark.parametrize("remove_tracking", [False, True])
@pytest.mark.parametrize("restart_count", [1, 3])
def test_recovered_mount_adds_service_pane_and_preserves_existing_panes(
    isolated_tmux_server: TmuxServer, remove_tracking: bool, restart_count: int
) -> None:
    server = isolated_tmux_server
    locations = {remote: str(server.directory / remote) for remote in ("odo", "odOracle")}
    mount_commands = {remote: f"""rclone mount {remote}: {shlex.quote(location)}""" for remote, location in locations.items()}
    script = build_tmux_launch_command(mount_commands=mount_commands, mount_locations=locations, session_name="cloud mount", unmounted_clouds=set())
    subprocess.run(["/bin/sh", "-c", script], cwd=server.directory, env=server.environment, capture_output=True, text=True, timeout=10, check=True)
    target = "=cloud mount:=odo"
    original_panes = _read_panes(server=server, target=target)
    original_commands: dict[str, str] = {}
    for pane in original_panes:
        _run_tmux(server=server, arguments=["wait-for", f"""{pane.identifier}-ready"""])
        original_commands[pane.identifier] = (server.directory / f"""{pane.identifier}.command""").read_text(encoding="utf-8")
    service_command = shlex.split(build_mount_pane_command(mount_command=mount_commands["odo"]))[2]
    service_pane = next(identifier for identifier, command in original_commands.items() if command == service_command)
    assert _run_tmux(server=server, arguments=["show-options", "-wqv", "-t", target, "@cloud-mount-service"]) == service_pane
    recovered_script = build_tmux_launch_command(
        mount_commands=mount_commands, mount_locations=locations, session_name="cloud mount", unmounted_clouds={"odo"}
    )
    subprocess.run(
        ["/bin/sh", "-c", recovered_script], cwd=server.directory, env=server.environment, capture_output=True, text=True, timeout=10, check=True
    )
    assert _read_panes(server=server, target=target) == original_panes
    _run_tmux(server=server, arguments=["kill-pane", "-t", service_pane])
    if remove_tracking:
        _run_tmux(server=server, arguments=["set-window-option", "-u", "-t", target, "@cloud-mount-service"])
    surviving_panes = _read_panes(server=server, target=target)
    other_panes = _read_panes(server=server, target="=cloud mount:=odOracle")

    restarts = [
        subprocess.Popen(
            ["/bin/sh", "-c", recovered_script], cwd=server.directory, env=server.environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        for _ in range(restart_count)
    ]
    for restart in restarts:
        _stdout, stderr = restart.communicate(timeout=10)
        assert restart.returncode == 0, stderr

    recovered_panes = _read_panes(server=server, target=target)
    assert len(recovered_panes) == 5
    assert all(pane in recovered_panes for pane in surviving_panes)
    new_pane = next(pane for pane in recovered_panes if pane not in surviving_panes)
    _run_tmux(server=server, arguments=["wait-for", f"""{new_pane.identifier}-ready"""])
    assert (server.directory / f"""{new_pane.identifier}.command""").read_text(encoding="utf-8") == service_command
    assert _run_tmux(server=server, arguments=["show-options", "-wqv", "-t", target, "@cloud-mount-service"]) == new_pane.identifier
    assert _read_panes(server=server, target="=cloud mount:=odOracle") == other_panes
    for pane in surviving_panes:
        assert (server.directory / f"""{pane.identifier}.command""").read_text(encoding="utf-8") == original_commands[pane.identifier]
