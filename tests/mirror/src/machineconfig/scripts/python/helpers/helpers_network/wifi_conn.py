from __future__ import annotations

from pathlib import Path
import subprocess

from machineconfig.scripts.python.helpers.helpers_network import wifi_conn as target


def _noop_print(*_args: object, **_kwargs: object) -> None:
    return None


def test_get_available_networks_deduplicates_windows_entries(monkeypatch: object) -> None:
    def fake_run(
        cmd: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        if cmd == ["netsh", "wlan", "show", "profiles"]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="""
All User Profile     : HomeWiFi
All User Profile     : CafeWiFi
""".strip(),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="""
SSID 1 : HomeWiFi
    Signal             : 83%
SSID 2 : AirportWiFi
    Signal             : 61%
""".strip(),
            stderr="",
        )

    monkeypatch.setattr(target.platform, "system", lambda: "Windows")
    monkeypatch.setattr(target.subprocess, "run", fake_run)
    monkeypatch.setattr(target.console, "print", _noop_print)

    networks = target.get_available_networks()

    assert networks == [
        {"ssid": "HomeWiFi", "signal": "Unknown"},
        {"ssid": "CafeWiFi", "signal": "Unknown"},
        {"ssid": "AirportWiFi", "signal": "61%"},
    ]


def test_try_config_connection_reads_cwd_wifi_ini(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    home_dir = tmp_path.joinpath("home")
    cwd_dir = tmp_path.joinpath("cwd")
    home_dir.mkdir()
    cwd_dir.mkdir()
    cwd_dir.joinpath("wifi.ini").write_text(
        """
[Lab]
SSID = LabSSID
pwd = supersecret
""".strip(),
        encoding="utf-8",
    )
    connect_calls: list[tuple[str, str]] = []

    class FakePath:
        @classmethod
        def home(cls) -> Path:
            return home_dir

        @classmethod
        def cwd(cls) -> Path:
            return cwd_dir

        def __new__(cls, value: str | Path) -> Path:
            return Path(value)

    monkeypatch.setattr(target, "Path", FakePath)
    monkeypatch.setattr(target, "connect_to_new_network", lambda ssid, password: connect_calls.append((ssid, password)))
    monkeypatch.setattr(target.console, "print", _noop_print)

    result = target.try_config_connection("Lab")

    assert result is True
    assert connect_calls == [("LabSSID", "supersecret")]


def test_manual_network_selection_requires_non_empty_password(monkeypatch: object) -> None:
    monkeypatch.setattr(target, "display_and_select_network", lambda: {"ssid": "CafeWiFi", "signal": "61%"})
    monkeypatch.setattr(target.getpass, "getpass", lambda _prompt: "")
    monkeypatch.setattr(target.console, "print", _noop_print)

    assert target.manual_network_selection() is False


def test_create_new_connection_linux_replaces_existing_profile(monkeypatch: object) -> None:
    commands: list[str] = []

    def fake_run(
        cmd: str,
        *,
        shell: bool,
        capture_output: bool = False,
        text: bool = False,
        check: bool,
    ) -> subprocess.CompletedProcess[bytes]:
        _ = (shell, capture_output, text, check)
        commands.append(cmd)
        return subprocess.CompletedProcess(args=[cmd], returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(target.platform, "system", lambda: "Linux")
    monkeypatch.setattr(target.subprocess, "run", fake_run)
    monkeypatch.setattr(target.console, "print", _noop_print)

    target.create_new_connection(name="Office", ssid="OfficeSSID", password="pw123")

    assert commands == [
        "nmcli connection show 'Office'",
        "nmcli connection delete 'Office'",
        "nmcli connection add type wifi con-name 'Office' ssid 'OfficeSSID' wifi-sec.key-mgmt wpa-psk wifi-sec.psk 'pw123'",
    ]
