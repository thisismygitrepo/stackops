from io import StringIO
from pathlib import Path

from rich.console import Console

from stackops.jobs.installer.python_scripts import rmpc


def _quiet_console() -> Console:
    return Console(file=StringIO(), force_terminal=False)


def test_choose_rmpc_mpd_address_prefers_working_socket(monkeypatch) -> None:
    monkeypatch.setattr(rmpc, "_mpd_endpoint_available", lambda address: address == rmpc.LINUX_MPD_SOCKET)

    address = rmpc._choose_rmpc_mpd_address(console=_quiet_console(), socket_path=rmpc.LINUX_MPD_SOCKET)

    assert address == rmpc.LINUX_MPD_SOCKET


def test_choose_rmpc_mpd_address_falls_back_to_default_tcp(monkeypatch) -> None:
    monkeypatch.setattr(rmpc, "_mpd_endpoint_available", lambda address: address == rmpc.DEFAULT_MPD_ADDRESS)

    address = rmpc._choose_rmpc_mpd_address(console=_quiet_console(), socket_path=rmpc.LINUX_MPD_SOCKET)

    assert address == rmpc.DEFAULT_MPD_ADDRESS


def test_write_rmpc_config_sets_ytdlp_remote_components(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(rmpc.shutil, "which", lambda _: None)

    rmpc._write_rmpc_youtube_config(console=_quiet_console(), mpd_address=rmpc.DEFAULT_MPD_ADDRESS)

    config_text = tmp_path.joinpath(".config", "rmpc", "config.ron").read_text(encoding="utf-8")
    assert 'address: "127.0.0.1:6600",' in config_text
    assert 'cache_dir: "' in config_text
    assert 'extra_yt_dlp_args: ["--remote-components", "ejs:github"],' in config_text
