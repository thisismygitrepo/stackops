import json
from pathlib import Path


def test_csvlens_installer_data_matches_release_assets() -> None:
    installer_data_path = Path(__file__).resolve().parent.parent / "src/machineconfig/jobs/installer/installer_data.json"
    installer_data = json.loads(installer_data_path.read_text(encoding="utf-8"))
    csvlens = next(installer for installer in installer_data["installers"] if installer["appName"] == "csvlens")

    assert csvlens["repoURL"] == "https://github.com/ys-l/csvlens"
    assert csvlens["fileNamePattern"]["amd64"]["linux"] == "csvlens-x86_64-unknown-linux-gnu.tar.xz"
    assert csvlens["fileNamePattern"]["amd64"]["darwin"] == "csvlens-x86_64-apple-darwin.tar.xz"
    assert csvlens["fileNamePattern"]["amd64"]["windows"] == "csvlens-x86_64-pc-windows-msvc.zip"
    assert csvlens["fileNamePattern"]["arm64"]["linux"] == "csvlens-aarch64-unknown-linux-gnu.tar.xz"
    assert csvlens["fileNamePattern"]["arm64"]["darwin"] == "csvlens-aarch64-apple-darwin.tar.xz"
    assert csvlens["fileNamePattern"]["arm64"]["windows"] == "csvlens-aarch64-pc-windows-msvc.zip"
