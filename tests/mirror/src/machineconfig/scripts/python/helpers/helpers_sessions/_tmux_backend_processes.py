from __future__ import annotations

from dataclasses import dataclass

import pytest

from machineconfig.scripts.python.helpers.helpers_sessions import _tmux_backend_processes as tmux_processes


@dataclass
class FakeProcess:
    pid: int
    proc_name: str
    proc_cmdline: list[str]
    proc_status: str
    started_at: float
    parent_proc: FakeProcess | None
    child_procs: list[FakeProcess]

    def name(self) -> str:
        return self.proc_name

    def cmdline(self) -> list[str]:
        return list(self.proc_cmdline)

    def is_running(self) -> bool:
        return self.proc_status != "stopped"

    def status(self) -> str:
        return self.proc_status

    def parent(self) -> FakeProcess | None:
        return self.parent_proc

    def create_time(self) -> float:
        return self.started_at

    def children(self, recursive: bool) -> list[FakeProcess]:
        if not recursive:
            return list(self.child_procs)
        descendants: list[FakeProcess] = []
        queue: list[FakeProcess] = list(self.child_procs)
        while queue:
            current = queue.pop(0)
            descendants.append(current)
            queue.extend(current.child_procs)
        return descendants


def test_find_meaningful_pane_process_label_prefers_non_shell_descendant(monkeypatch: pytest.MonkeyPatch) -> None:
    root = FakeProcess(100, "bash", ["bash"], "sleeping", 1.0, None, [])
    shell = FakeProcess(101, "bash", ["bash"], "sleeping", 2.0, root, [])
    editor = FakeProcess(102, "vim", ["vim", "/tmp/todo.txt"], "running", 3.0, shell, [])
    root.child_procs = [shell]
    shell.child_procs = [editor]

    def fake_process(pid: int) -> FakeProcess:
        assert pid == 100
        return root

    monkeypatch.setattr(tmux_processes.psutil, "Process", fake_process)

    label = tmux_processes.find_meaningful_pane_process_label("100")

    assert label == "vim todo.txt"


def test_find_meaningful_pane_process_label_uses_meaningful_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    root = FakeProcess(200, "bash", ["bash"], "sleeping", 1.0, None, [])
    shell = FakeProcess(201, "bash", ["bash", "/tmp/build.sh"], "running", 2.0, root, [])
    root.child_procs = [shell]

    def fake_process(pid: int) -> FakeProcess:
        assert pid == 200
        return root

    monkeypatch.setattr(tmux_processes.psutil, "Process", fake_process)

    label = tmux_processes.find_meaningful_pane_process_label("200")

    assert label == "bash build.sh"
    assert tmux_processes.find_meaningful_pane_process_label("not-a-pid") is None


def test_classify_pane_status_handles_dead_shell_running_and_unknown() -> None:
    def fake_child_label(_: str) -> str | None:
        return "pytest worker"

    dead = tmux_processes.classify_pane_status(
        {"pane_command": "bash", "pane_dead": "dead", "pane_dead_status": "3", "pane_pid": "100"}, pane_process_label_finder=fake_child_label
    )
    shell_running = tmux_processes.classify_pane_status(
        {"pane_command": "bash", "pane_dead": "", "pane_dead_status": "", "pane_pid": "100"}, pane_process_label_finder=fake_child_label
    )
    shell_idle = tmux_processes.classify_pane_status(
        {"pane_command": "zsh", "pane_dead": "", "pane_dead_status": "", "pane_pid": "100"}, pane_process_label_finder=lambda _: None
    )
    command_running = tmux_processes.classify_pane_status(
        {"pane_command": "vim", "pane_dead": "", "pane_dead_status": "", "pane_pid": "100"}, pane_process_label_finder=fake_child_label
    )
    unknown = tmux_processes.classify_pane_status(
        {"pane_command": "", "pane_dead": "", "pane_dead_status": "", "pane_pid": "100"}, pane_process_label_finder=fake_child_label
    )

    assert dead == ("bash", "exited (code 3)")
    assert shell_running == ("pytest worker", "running: `pytest worker`")
    assert shell_idle == ("zsh", "idle shell")
    assert command_running == ("vim", "running: `vim`")
    assert unknown == ("—", "unknown")
