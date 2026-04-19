

import subprocess
from pathlib import Path

import pytest

from stackops.jobs.installer.python_scripts import cloudflare_warp_cli as cloudflare_warp_cli_module
from stackops.utils.schemas.installer.installer_types import InstallerData


def _build_installer_data() -> InstallerData:
    return {
        "appName": "Cloudflare WARP CLI",
        "license": "Proprietary",
        "doc": "VPN",
        "repoURL": "CMD",
        "fileNamePattern": {"amd64": {"windows": None, "linux": None, "darwin": None}, "arm64": {"windows": None, "linux": None, "darwin": None}},
    }


def test_main_runs_linux_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "cloudflare_warp_cli.sh"
    script_path.write_text("echo warp-linux\n", encoding="utf-8")
    called: dict[str, object] = {}

    def fake_run(program: str, shell: bool, check: bool) -> subprocess.CompletedProcess[str]:
        called["program"] = program
        called["shell"] = shell
        called["check"] = check
        return subprocess.CompletedProcess(args=program, returncode=0)

    monkeypatch.setattr(cloudflare_warp_cli_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cloudflare_warp_cli_module, "get_path_reference_path", lambda module, path_reference: script_path)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = cloudflare_warp_cli_module.main(_build_installer_data(), version=None, update=False)

    assert called == {"program": "echo warp-linux\n", "shell": True, "check": True}
    assert result == "Cloudflare WARP CLI installed successfully on Linux."


def test_main_uses_brew_on_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_run(program: str, shell: bool, check: bool) -> subprocess.CompletedProcess[str]:
        called["program"] = program
        called["shell"] = shell
        called["check"] = check
        return subprocess.CompletedProcess(args=program, returncode=0)

    monkeypatch.setattr(cloudflare_warp_cli_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = cloudflare_warp_cli_module.main(_build_installer_data(), version="latest", update=False)

    assert called == {"program": "brew install --cask cloudflare-warp", "shell": True, "check": True}
    assert result == "Cloudflare WARP CLI installed successfully on Darwin."


@pytest.mark.parametrize(
    ("platform_name", "message"), [("Windows", "Installer is not yet implemented for Windows."), ("Plan9", "Unsupported platform: Plan9")]
)
def test_main_rejects_unsupported_platforms(monkeypatch: pytest.MonkeyPatch, platform_name: str, message: str) -> None:
    monkeypatch.setattr(cloudflare_warp_cli_module.platform, "system", lambda: platform_name)

    with pytest.raises(NotImplementedError, match=message):
        cloudflare_warp_cli_module.main(_build_installer_data(), version=None, update=False)
