from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_process_commands import (
    select_current_pane_process_argv,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection import (
    PaneProcess,
)


def test_current_command_prefers_matching_uv_process_over_deep_python_child() -> None:
    processes = [
        PaneProcess(pid=100, name="zsh", argv=("zsh",), depth=0, started_at=1.0),
        PaneProcess(
            pid=101,
            name="uv",
            argv=("uv", "run", "python", "-m", "worker", "--count", "2"),
            depth=1,
            started_at=2.0,
        ),
        PaneProcess(
            pid=102,
            name="python",
            argv=("python", "-m", "worker", "--count", "2"),
            depth=2,
            started_at=3.0,
        ),
    ]

    selected_argv = select_current_pane_process_argv(
        pane_command="uv",
        processes=processes,
    )

    assert selected_argv == ("uv", "run", "python", "-m", "worker", "--count", "2")


def test_shell_current_command_prefers_shallow_non_shell_child() -> None:
    processes = [
        PaneProcess(pid=100, name="zsh", argv=("zsh",), depth=0, started_at=1.0),
        PaneProcess(pid=101, name="nvim", argv=("nvim", "."), depth=1, started_at=2.0),
        PaneProcess(
            pid=102,
            name="node",
            argv=("node", "/tmp/language-server.js"),
            depth=2,
            started_at=3.0,
        ),
    ]

    selected_argv = select_current_pane_process_argv(
        pane_command="zsh",
        processes=processes,
    )

    assert selected_argv == ("nvim", ".")


def test_idle_shell_current_command_has_no_process_argv() -> None:
    selected_argv = select_current_pane_process_argv(
        pane_command="zsh",
        processes=[
            PaneProcess(pid=100, name="zsh", argv=("zsh",), depth=0, started_at=1.0),
        ],
    )

    assert selected_argv is None
