from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType

import pytest

import machineconfig.scripts.python.helpers.helpers_search.script_help as script_help


def test_get_custom_roots_reads_only_existing_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    valid_root = tmp_path / "custom_scripts"
    valid_root.mkdir()
    missing_root = tmp_path / "missing_scripts"
    defaults_path = tmp_path / "defaults.ini"
    defaults_path.write_text(
        f"""[general]
scripts = {valid_root}, {missing_root}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(script_help, "DEFAULTS_PATH", defaults_path)

    assert script_help.get_custom_roots("scripts") == [valid_root.resolve()]


def test_list_available_scripts_groups_public_files_by_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    public_root = tmp_path / "config_root"
    scripts_root = public_root / "scripts"
    (scripts_root / "nested").mkdir(parents=True)
    (scripts_root / "task.py").write_text("print('x')\n", encoding="utf-8")
    (scripts_root / "nested" / "run.sh").write_text("echo x\n", encoding="utf-8")
    (scripts_root / "plain").write_text("x\n", encoding="utf-8")

    monkeypatch.setattr(script_help, "CONFIG_ROOT", public_root)

    script_help.list_available_scripts("public")

    output = capsys.readouterr().out
    assert "PUBLIC" in output
    assert "[.py]" in output
    assert "[.sh]" in output
    assert "[other]" in output
    assert "task.py" in output
    assert "nested/run.sh" in output
    assert "plain" in output


def test_list_available_scripts_reports_dynamic_fetch_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake_requests = ModuleType("requests")

    class FakeResponse:
        status_code: int = 503

    def fake_get(url: str, timeout: int) -> FakeResponse:
        _ = url
        _ = timeout
        return FakeResponse()

    setattr(fake_requests, "get", fake_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    script_help.list_available_scripts("dynamic")

    output = capsys.readouterr().out
    assert "Could not fetch from GitHub (status: 503)" in output
