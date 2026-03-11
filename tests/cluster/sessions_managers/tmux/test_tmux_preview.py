from subprocess import CompletedProcess

from machineconfig.scripts.python.helpers.helpers_sessions import _tmux_backend


def test_classify_pane_status_marks_shell_with_running_child(monkeypatch) -> None:
    monkeypatch.setattr(_tmux_backend, "_find_meaningful_pane_process_label", lambda pane_pid: "sleep 30")

    process_name, status = _tmux_backend._classify_pane_status(
        {
            "pane_command": "bash",
            "pane_dead": "",
            "pane_pid": "1234",
        }
    )

    assert process_name == "sleep 30"
    assert status == "running: `sleep 30`"


def test_build_preview_shows_child_process_for_shell_pane(monkeypatch) -> None:
    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        if args[:3] == ["tmux", "list-windows", "-t"]:
            return CompletedProcess(args=args, returncode=0, stdout="1\tdemo\t1\tactive\n", stderr="")
        if args[:3] == ["tmux", "list-panes", "-s"]:
            return CompletedProcess(
                args=args,
                returncode=0,
                stdout="1\t1\t/tmp\tbash\tactive\t\t\t4242\n",
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(_tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(_tmux_backend, "_find_meaningful_pane_process_label", lambda pane_pid: "sleep 30")

    preview = _tmux_backend._build_preview("demo")

    assert "| 1 | demo | 1 ⇐ | sleep 30 | running: `sleep 30` | `/tmp` |" in preview
