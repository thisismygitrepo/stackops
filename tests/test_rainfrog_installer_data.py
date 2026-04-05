import json
from pathlib import Path


def test_rainfrog_linux_installer_uses_gnu_binaries() -> None:
    installer_data_path = Path(__file__).resolve().parent.parent / "src/machineconfig/jobs/installer/installer_data.json"
    installer_data = json.loads(installer_data_path.read_text(encoding="utf-8"))
    rainfrog = next(installer for installer in installer_data["installers"] if installer["appName"] == "rainfrog")

    assert rainfrog["fileNamePattern"]["amd64"]["linux"].endswith("x86_64-unknown-linux-gnu.tar.gz")
    assert rainfrog["fileNamePattern"]["arm64"]["linux"].endswith("aarch64-unknown-linux-gnu.tar.gz")
