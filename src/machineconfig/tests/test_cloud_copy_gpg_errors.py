from pathlib import Path
from types import ModuleType
import sys

import pytest

from machineconfig.scripts.python.helpers.helpers_cloud import cloud_copy
from machineconfig.utils.io import GpgCommandError


class _FailingPathExtended:
    def __init__(self, value: str) -> None:
        self.value = value

    def from_cloud(
        self,
        *,
        cloud: str,
        remotepath: str,
        unzip: bool,
        decrypt: bool,
        pwd: str | None,
        overwrite: bool,
        rel2home: bool,
        os_specific: bool,
        root: str,
        strict: bool,
    ) -> None:
        raise GpgCommandError(
            command=["gpg", "--batch", "--yes", "--decrypt", "--output", self.value, f"{self.value}.gpg"],
            returncode=2,
            stdout="",
            stderr="gpg: decryption failed: No secret key\n",
            hint="No matching private key is available in the current GPG keyring.",
        )


def test_cloud_copy_download_prints_gpg_failure_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_path_extended_module = ModuleType("machineconfig.utils.path_extended")
    fake_path_extended_module.PathExtended = _FailingPathExtended  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "machineconfig.utils.path_extended", fake_path_extended_module)

    fake_helpers2_module = ModuleType("machineconfig.scripts.python.helpers.helpers_cloud.helpers2")

    def fake_parse_cloud_source_target(**_: object) -> tuple[str, str, str]:
        return "demo", "demo:archive/plain.gpg", str(tmp_path.joinpath("plain.txt"))

    fake_helpers2_module.parse_cloud_source_target = fake_parse_cloud_source_target  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_cloud.helpers2", fake_helpers2_module)

    with pytest.raises(SystemExit) as exc_info:
        cloud_copy.main(
            source="demo:archive/plain.gpg",
            target=str(tmp_path.joinpath("plain.txt")),
            overwrite=False,
            share=False,
            rel2home=False,
            root="myhome",
            key=None,
            pwd=None,
            encrypt=True,
            zip_=False,
            os_specific=False,
            config=None,
        )

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "GPG command failed." in captured.out
    assert "Command: gpg --batch --yes --decrypt --output" in captured.out
    assert "gpg: decryption failed: No secret key" in captured.out