import sys
import types

import pytest

import machineconfig.scripts.python.helpers.helpers_network.address_switch as subject

_INSTALLER_MODULE = "machineconfig.utils.installer_utils.installer_cli"



def _install_warp_stub(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None, bool]]:
    installer_calls: list[tuple[str, str | None, bool]] = []

    def fake_install_if_missing(*, which: str, binary_name: str | None, verbose: bool) -> None:
        installer_calls.append((which, binary_name, verbose))

    installer_module = types.ModuleType(_INSTALLER_MODULE)
    setattr(installer_module, "install_if_missing", fake_install_if_missing)
    monkeypatch.setitem(sys.modules, _INSTALLER_MODULE, installer_module)
    return installer_calls



def test_ip_is_acceptable_obeys_target_and_current_values() -> None:
    assert subject._ip_is_acceptable("2.2.2.2", "1.1.1.1", None) is True
    assert subject._ip_is_acceptable("1.1.1.1", "1.1.1.1", None) is False
    assert subject._ip_is_acceptable("9.9.9.9", "1.1.1.1", ["9.9.9.9"]) is True
    assert subject._ip_is_acceptable("8.8.8.8", "1.1.1.1", ["9.9.9.9"]) is False



def test_switch_public_ip_address_returns_current_ip_when_already_target(monkeypatch: pytest.MonkeyPatch) -> None:
    installer_calls = _install_warp_stub(monkeypatch)
    subprocess_calls: list[list[str]] = []
    monkeypatch.setattr(subject, "get_public_ip_address", lambda: {"ip": "1.1.1.1"})
    monkeypatch.setattr(subject.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda args, *, check: subprocess_calls.append(args) or types.SimpleNamespace(returncode=0),
    )

    result = subject.switch_public_ip_address(
        max_trials=3,
        wait_seconds=0.0,
        target_ip_addresses=["1.1.1.1"],
    )

    assert installer_calls == [("warp-cli", None, True)]
    assert subprocess_calls == []
    assert result == (True, "1.1.1.1")



def test_switch_public_ip_address_returns_success_after_new_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_warp_stub(monkeypatch)
    responses = iter([{"ip": "1.1.1.1"}, {"ip": "2.2.2.2"}])
    subprocess_calls: list[list[str]] = []
    sleep_calls: list[float] = []

    def fake_get_public_ip_address() -> dict[str, str]:
        return next(responses)

    def fake_run(args: list[str], *, check: bool) -> types.SimpleNamespace:
        subprocess_calls.append(args)
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(subject, "get_public_ip_address", fake_get_public_ip_address)
    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    monkeypatch.setattr(subject.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = subject.switch_public_ip_address(
        max_trials=1,
        wait_seconds=0.5,
        target_ip_addresses=None,
    )

    assert result == (True, "2.2.2.2")
    assert subprocess_calls == [
        ["warp-cli", "registration", "delete"],
        ["warp-cli", "registration", "new"],
        ["warp-cli", "connect"],
        ["warp-cli", "status"],
    ]
    assert sleep_calls == [0.5, 0.5]



def test_switch_public_ip_address_returns_failure_after_exhausting_trials(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_warp_stub(monkeypatch)
    monkeypatch.setattr(subject, "get_public_ip_address", lambda: {"ip": "1.1.1.1"})
    monkeypatch.setattr(subject.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda _args, *, check: types.SimpleNamespace(returncode=0),
    )

    result = subject.switch_public_ip_address(
        max_trials=2,
        wait_seconds=0.0,
        target_ip_addresses=None,
    )

    assert result == (False, "1.1.1.1")
