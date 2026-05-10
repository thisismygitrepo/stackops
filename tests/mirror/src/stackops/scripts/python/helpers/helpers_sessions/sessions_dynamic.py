import platform

import pytest

from stackops.scripts.python.helpers.helpers_sessions import sessions_dynamic


def test_validate_backend_accepts_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert sessions_dynamic._validate_backend("tmux") == "tmux"


def test_validate_backend_auto_picks_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert sessions_dynamic._validate_backend("auto") == "tmux"


def test_validate_backend_still_rejects_zellij_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    with pytest.raises(ValueError, match="zellij"):
        sessions_dynamic._validate_backend("zellij")