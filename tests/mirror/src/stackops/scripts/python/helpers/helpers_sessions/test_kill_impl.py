import pytest

from stackops.scripts.python.helpers.helpers_sessions import kill_impl
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer


def _install_fakes(monkeypatch: pytest.MonkeyPatch, available_names: list[str]) -> list[str | None]:
    exact_calls: list[str | None] = []

    def fake_exact(
        backend: SessionMultiplexer, name: str | None, kill_all: bool, idle: bool, window: bool, delete: bool
    ) -> tuple[str, str | None, list[KilledTarget]]:
        exact_calls.append(name)
        return ("run_script", f"kill {name}", [])

    def fake_list(backend: SessionMultiplexer, delete: bool) -> list[str] | None:
        return available_names

    monkeypatch.setattr(kill_impl, "_choose_exact_kill_target", fake_exact)
    monkeypatch.setattr(kill_impl, "_list_killable_session_names", fake_list)
    return exact_calls


def test_comma_separated_names_and_globs_are_resolved_deduplicated_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    exact_calls = _install_fakes(monkeypatch=monkeypatch, available_names=["api", "web1", "web2", "db"])

    action, payload, _killed = kill_impl.choose_kill_target(
        backend="tmux", name=" db , web* ,web1", kill_all=False, idle=False, window=False, delete=False
    )

    assert action == "run_script"
    assert exact_calls == ["db", "web1", "web2"]
    assert payload == "kill db\nkill web1\nkill web2"


def test_single_exact_name_goes_straight_to_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    exact_calls = _install_fakes(monkeypatch=monkeypatch, available_names=[])

    action, payload, _killed = kill_impl.choose_kill_target(
        backend="tmux", name="api", kill_all=False, idle=False, window=False, delete=False
    )

    assert (action, payload, exact_calls) == ("run_script", "kill api", ["api"])


def test_unmatched_glob_aborts_before_any_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    exact_calls = _install_fakes(monkeypatch=monkeypatch, available_names=["api"])

    action, payload, _killed = kill_impl.choose_kill_target(
        backend="tmux", name="api,web*", kill_all=False, idle=False, window=False, delete=False
    )

    assert action == "error"
    assert payload is not None and "web*" in payload
    assert exact_calls == []


@pytest.mark.parametrize("name", ["api,", ",api", "api,,web", " "])
def test_empty_selector_is_rejected(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    exact_calls = _install_fakes(monkeypatch=monkeypatch, available_names=["api", "web"])

    action, _payload, _killed = kill_impl.choose_kill_target(
        backend="tmux", name=name, kill_all=False, idle=False, window=False, delete=False
    )

    assert action == "error"
    assert exact_calls == []
