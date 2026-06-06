from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend as herdr


def _completed(args: list[str], stdout: str, returncode: int = 0) -> CompletedProcess[str]:
    return CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr="")


def test_choose_named_session_uses_herdr_attach() -> None:
    assert herdr.choose_session(name="default", new_session=False, kill_all=False) == (
        "handoff_script",
        "herdr session attach default",
    )


def test_new_session_uses_generated_herdr_session_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(herdr, "_new_session_name", lambda: "stackops-test")

    assert herdr.new_session_script(kill_all=False) == "herdr --session stackops-test"


def test_kill_all_stops_running_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [
        {"name": "default", "running": True},
        {"name": "stopped", "running": False},
        {"name": "agent work", "running": True},
    ]
    monkeypatch.setattr(herdr, "_session_entries", lambda: sessions)

    assert herdr.choose_kill_target(name=None, kill_all=True) == (
        "run_script",
        "herdr session stop default --json\nherdr session stop 'agent work' --json",
    )


def test_window_selection_builds_tab_and_pane_attach_scripts(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        _ = timeout
        if args == ["herdr", "--session", "default", "tab", "list"]:
            return _completed(
                args,
                (
                    '{"result":{"tabs":['
                    '{"tab_id":"workspace:1","number":1,"label":"main","focused":true}'
                    ']}}'
                ),
            )
        if args == ["herdr", "--session", "default", "pane", "list"]:
            return _completed(
                args,
                (
                    '{"result":{"panes":['
                    '{"pane_id":"pane-1","terminal_id":"term-1","tab_id":"workspace:1",'
                    '"label":"codex","focused":false}'
                    ']}}'
                ),
            )
        return _completed(args, "{}", returncode=1)

    monkeypatch.setattr(herdr, "run_command", fake_run_command)
    monkeypatch.setattr(
        herdr,
        "_session_entries",
        lambda: [{"name": "default", "running": True, "default": True}],
    )
    monkeypatch.setattr(
        herdr,
        "interactive_choose_with_preview",
        lambda msg, options_to_preview_mapping, multi=False: "[default] 1:main / codex",
    )

    action, script = herdr.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=True,
    )

    assert action == "handoff_script"
    assert script == (
        "herdr --session default agent focus term-1\n"
        "herdr session attach default"
    )
