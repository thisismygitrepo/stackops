import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper import get_command_streamlit
from stackops.scripts.python.helpers.helpers_fire_command import fire_jobs_impl
from stackops.utils import dashboard_streamlit
from stackops.utils.installer_utils import installer_cli
from stackops.utils.network import address


@pytest.mark.parametrize("port_setting, expected_port", [("", 8501), ("port = 45000", 45000)])
def test_streamlit_command_uses_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, port_setting: str, expected_port: int, capsys: pytest.CaptureFixture[str],
) -> None:
    config_dir = tmp_path / ".streamlit"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(f"""[server]\n{port_setting}\n""", encoding="utf-8")
    monkeypatch.setattr(address, "select_lan_ipv4", lambda prefer_vpn: None)
    monkeypatch.setattr(installer_cli, "install_if_missing", lambda **kwargs: None)
    command = get_command_streamlit(tmp_path / "dashboard.py")
    assert shlex.split(command) == ["python", "-m", "stackops.utils.dashboard_streamlit", "--port", str(expected_port), "--"]
    assert "app is running" not in capsys.readouterr().out


@pytest.mark.parametrize("port_value", ['"45000"', "true", "0", "65536"])
def test_streamlit_config_rejects_invalid_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, port_value: str) -> None:
    config_dir = tmp_path / ".streamlit"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(f"""[server]\nport = {port_value}\n""", encoding="utf-8")
    monkeypatch.setattr(address, "select_lan_ipv4", lambda prefer_vpn: None)
    with pytest.raises(ValueError, match="server.port"):
        get_command_streamlit(tmp_path / "dashboard.py")


def test_streamlit_entrypoint_uses_active_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "dashboard with spaces.py"
    script.touch()
    calls: list[tuple[str, ...]] = []

    def capture_launch(
        *, command: tuple[str, ...], port: int, identity: str, cwd: Path,
        environment: dict[str, str], health_path: str, state_dir: Path,
    ) -> int:
        assert port == 45000
        assert identity == f"""Streamlit {script.name}"""
        assert cwd == Path.cwd()
        assert environment == {}
        assert health_path == "/_stcore/health"
        assert state_dir.name == "dashboards"
        calls.append(command)
        return 7

    monkeypatch.setattr(dashboard_streamlit, "run_dashboard", capture_launch)
    monkeypatch.setattr(sys, "argv", ["dashboard_streamlit", "--port", "45000", "--", str(script)])
    assert dashboard_streamlit.main() == 7
    assert calls == [(
        sys.executable, "-m", "streamlit", "run", "--server.address", "0.0.0.0",
        "--server.headless", "true", "--server.port", "45000", str(script),
    )]


@pytest.mark.parametrize("hold_directory", [False, True])
def test_streamlit_shell_preserves_failure_status(tmp_path: Path, hold_directory: bool) -> None:
    script = tmp_path / "app directory" / "dashboard file.py"
    script.parent.mkdir()
    script.touch()
    command = fire_jobs_impl._build_final_command(
        debug=False, module=False, streamlit=True, hold_directory=hold_directory, cmd=False,
        exe_line="sh -c 'exit 17' --", choice_file=script, choice_file_adjusted=str(script),
        choice_function=None, fire_args="",
    )
    result = subprocess.run(["bash", "-c", command], cwd=tmp_path, check=False)
    assert result.returncode == 17
