import pytest

from stackops.cluster.sessions_managers.tmux.tmux_utils import tmux_execution
from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend_options


def test_attach_script_for_target_uses_powershell_quoting_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tmux_execution.platform, "system", lambda: "Windows")

    script = _tmux_backend_options.attach_script_for_target(
        session_name="demo session",
        quote_fn=lambda value: f"BAD({value})",
        window_target="2",
        pane_index="1",
    )

    assert script == "\n".join(
        [
            "tmux select-window -t 'demo session:2'",
            "tmux select-pane -t 'demo session:2.1'",
            "if ($env:TMUX) { tmux switch-client -t 'demo session' } else { tmux attach -t 'demo session' }",
        ]
    )