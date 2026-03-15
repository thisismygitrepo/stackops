from machineconfig.cluster.sessions_managers.tmux.tmux_utils.tmux_helpers import build_tmux_attach_or_switch_command
from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend import choose_session
from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend_options import attach_script_for_target
from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import quote


def test_build_tmux_attach_or_switch_command_uses_switch_client_inside_tmux() -> None:
    command = build_tmux_attach_or_switch_command(session_name="m")

    assert 'if [ -n "${TMUX:-}" ]; then' in command
    assert "tmux switch-client -t m;" in command
    assert "tmux attach -t m;" in command


def test_attach_script_for_target_keeps_target_selection_before_attach_or_switch() -> None:
    script = attach_script_for_target(session_name="m", quote_fn=quote, window_target="1", pane_index="2")

    assert "tmux select-window -t m:1" in script
    assert "tmux select-pane -t m:1.2" in script
    assert "tmux switch-client -t m;" in script
    assert "tmux attach -t m;" in script
    assert "tmux attach -t m\n" not in script


def test_choose_session_named_target_uses_attach_or_switch_script() -> None:
    action, payload = choose_session(name="m", new_session=False, kill_all=False, window=False)

    assert action == "run_script"
    assert payload is not None
    assert "tmux switch-client -t m;" in payload
    assert "tmux attach -t m;" in payload
