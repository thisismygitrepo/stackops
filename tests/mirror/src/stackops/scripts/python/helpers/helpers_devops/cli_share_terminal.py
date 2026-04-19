

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest
import typer

from stackops.scripts.python.helpers.helpers_devops import cli_share_terminal as module


@dataclass
class FakePopenProcess:
    command: str
    shell: bool
    terminated: bool = False
    waited: bool = False

    def __enter__(self) -> FakePopenProcess:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self) -> None:
        self.waited = True


def install_share_terminal_network_stub(monkeypatch: pytest.MonkeyPatch, lan_ip: str | None) -> None:
    import stackops.scripts.python.helpers as helpers_package

    helpers_network_module = ModuleType("stackops.scripts.python.helpers.helpers_network")
    address_module = ModuleType("stackops.scripts.python.helpers.helpers_network.address")

    def fake_select_lan_ipv4(*, prefer_vpn: bool) -> str | None:
        assert prefer_vpn is False
        return lan_ip

    setattr(address_module, "select_lan_ipv4", fake_select_lan_ipv4)
    setattr(helpers_network_module, "address", address_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_network", helpers_network_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_network.address", address_module)
    monkeypatch.setattr(helpers_package, "helpers_network", helpers_network_module, raising=False)


def test_share_terminal_reads_password_file_and_launches_ttyd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import getpass
    import platform

    install_share_terminal_network_stub(monkeypatch, "10.0.0.9")
    displayed_urls: list[tuple[str, int, str]] = []
    processes: list[FakePopenProcess] = []
    home_dir = tmp_path.joinpath("home")
    password_file = home_dir.joinpath("dotfiles/creds/passwords/quick_password")
    password_file.parent.mkdir(parents=True)
    password_file.write_text("secret-pass\n", encoding="utf-8")

    def fake_display_terminal_url(local_ip_v4: str, port: int, protocol: str = "http") -> None:
        displayed_urls.append((local_ip_v4, port, protocol))

    def fake_popen(command: str, *, shell: bool) -> FakePopenProcess:
        process = FakePopenProcess(command=command, shell=shell)
        processes.append(process)
        return process

    def fake_sleep(seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "display_terminal_url", fake_display_terminal_url)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    monkeypatch.setattr(getpass, "getuser", lambda: "alex")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    module.share_terminal(
        port=None,
        username=None,
        password=None,
        no_auth=False,
        start_command=None,
        ssl=False,
        ssl_cert=None,
        ssl_key=None,
        ssl_ca=None,
        over_internet=False,
        install_missing_dependencies=False,
    )

    assert displayed_urls == [("10.0.0.9", 7681, "http")]
    assert len(processes) == 1
    assert processes[0].shell is True
    assert '--credential "alex:secret-pass"' in processes[0].command
    assert processes[0].command.endswith(" bash")
    assert processes[0].terminated is True
    assert processes[0].waited is True


def test_share_terminal_requires_password_when_default_file_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_dir = tmp_path.joinpath("home")
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))

    with pytest.raises(typer.Exit) as exc_info:
        module.share_terminal(
            port=None,
            username="alex",
            password=None,
            no_auth=False,
            start_command=None,
            ssl=False,
            ssl_cert=None,
            ssl_key=None,
            ssl_ca=None,
            over_internet=False,
            install_missing_dependencies=False,
        )

    assert exc_info.value.exit_code == 1


def test_share_terminal_requires_existing_ssl_files() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        module.share_terminal(
            port=None,
            username="alex",
            password="secret",
            no_auth=False,
            start_command=None,
            ssl=True,
            ssl_cert="/tmp/missing-cert.pem",
            ssl_key="/tmp/missing-key.pem",
            ssl_ca=None,
            over_internet=False,
            install_missing_dependencies=False,
        )

    assert exc_info.value.exit_code == 1


def test_main_with_parser_uses_typer_run(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded_targets: list[object] = []

    def fake_run(target: object) -> None:
        recorded_targets.append(target)

    monkeypatch.setattr(module.typer, "run", fake_run)

    module.main_with_parser()

    assert recorded_targets == [module.share_terminal]
