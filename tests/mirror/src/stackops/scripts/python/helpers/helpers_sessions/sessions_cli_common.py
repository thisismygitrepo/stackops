import platform

from stackops.scripts.python.helpers.helpers_sessions import sessions_cli_common


def test_resolve_standard_backend_accepts_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert sessions_cli_common.resolve_standard_backend("tmux") == "tmux"


def test_resolve_standard_backend_auto_still_prefers_windows_terminal_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert sessions_cli_common.resolve_standard_backend("auto") == "windows-terminal"