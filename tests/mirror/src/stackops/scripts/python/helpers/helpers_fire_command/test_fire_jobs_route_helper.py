from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_fire_command import fire_jobs_route_helper
from stackops.utils import meta
from stackops.utils.installer_utils import installer_cli
from stackops.utils.network import address


def test_get_command_streamlit_continues_without_lan_ipv4(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    printed_scripts: list[str] = []
    monkeypatch.setattr(address, "select_lan_ipv4", lambda prefer_vpn: None)
    monkeypatch.setattr(installer_cli, "install_if_missing", lambda which, binary_name, verbose: None)
    monkeypatch.setattr(meta, "print_code", lambda code, lexer, desc: printed_scripts.append(code))
    monkeypatch.setattr(fire_jobs_route_helper.platform, "node", lambda: "container-host")

    command = fire_jobs_route_helper.get_command_streamlit(choice_file=tmp_path / "app.py")

    assert command == "streamlit run --server.address 0.0.0.0 --server.headless true --server.port 8501"
    assert printed_scripts == [
        'qrterminal "http://container-host:8501"\necho "http://container-host:8501"\nqrterminal "http://localhost:8501"\necho "http://localhost:8501"'
    ]
    assert "None" not in printed_scripts[0]
