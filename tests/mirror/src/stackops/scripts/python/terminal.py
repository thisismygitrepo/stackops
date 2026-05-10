import platform

from stackops.scripts.python import terminal


def test_resolve_session_backend_accepts_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert terminal._resolve_session_backend("tmux") == "tmux"


def test_resolve_session_backend_auto_picks_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert terminal._resolve_session_backend("auto") == "tmux"