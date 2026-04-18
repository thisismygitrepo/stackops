from __future__ import annotations

import io
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from stackops.jobs.installer.checks import vt_utils

if TYPE_CHECKING:
    import vt


class _FakeVtClient:
    def __init__(self, token: str) -> None:
        self.token = token


class _EnumLike:
    def __init__(self, value: str | None) -> None:
        self.value = value


class _UnusedClient:
    def scan_file(self, _file_handle: object) -> object:
        raise AssertionError("directory inputs must return before scan_file runs")

    def get_object(self, _path: str, _analysis_id: str) -> object:
        raise AssertionError("directory inputs must return before get_object runs")


class _FakeScanClient:
    def __init__(self, responses: Sequence[object]) -> None:
        self.responses = list(responses)
        self.scanned_payloads: list[bytes] = []
        self.requested_paths: list[tuple[str, str]] = []

    def scan_file(self, file_handle: io.BytesIO) -> SimpleNamespace:
        self.scanned_payloads.append(file_handle.read())
        return SimpleNamespace(id="analysis-123")

    def get_object(self, path_template: str, analysis_id: str) -> object:
        self.requested_paths.append((path_template, analysis_id))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_get_vt_client_raises_when_token_file_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    with pytest.raises(FileNotFoundError, match="VirusTotal token not found"):
        vt_utils.get_vt_client()


def test_get_vt_client_reads_first_token_line(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home"
    token_path = fake_home / "dotfiles" / "creds" / "tokens"
    token_path.mkdir(parents=True)
    token_path.joinpath("virustotal").write_text(
        "token-123\nignored-second-line\n",
        encoding="utf-8",
    )
    fake_vt_module = ModuleType("vt")
    setattr(fake_vt_module, "Client", _FakeVtClient)

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setitem(sys.modules, "vt", fake_vt_module)

    client = vt_utils.get_vt_client()

    assert isinstance(client, _FakeVtClient)
    assert client.token == "token-123"


def test_scan_file_skips_directories(tmp_path: Path) -> None:
    directory_path = tmp_path / "nested"
    directory_path.mkdir()

    summary, results = vt_utils.scan_file(
        path=directory_path,
        client=cast("vt.Client", _UnusedClient()),
    )

    assert summary is None
    assert results == []


def test_scan_file_retries_then_returns_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "payload.bin"
    file_path.write_bytes(b"payload")
    sleep_calls: list[int] = []
    client = _FakeScanClient(
        responses=[
            RuntimeError("transient"),
            SimpleNamespace(status="queued", results=[]),
            SimpleNamespace(
                status="completed",
                results=[
                    SimpleNamespace(category=_EnumLike("malicious"), result=_EnumLike("trojan")),
                    SimpleNamespace(category=_EnumLike("harmless"), result=None),
                    SimpleNamespace(category=_EnumLike("timeout"), result=None),
                ],
            ),
        ]
    )

    monkeypatch.setattr(vt_utils.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    summary, results = vt_utils.scan_file(
        path=file_path,
        client=cast("vt.Client", client),
    )

    assert client.scanned_payloads == [b"payload"]
    assert client.requested_paths == [
        ("/analyses/{}", "analysis-123"),
        ("/analyses/{}", "analysis-123"),
        ("/analyses/{}", "analysis-123"),
    ]
    assert sleep_calls == [5, 10, 10]
    assert results == [
        {"engine_name": "engine_001", "category": "malicious", "result": "trojan"},
        {"engine_name": "engine_002", "category": "harmless", "result": None},
        {"engine_name": "engine_003", "category": "timeout", "result": None},
    ]
    assert summary == {
        "positive_pct": 50.0,
        "total_engines": 3,
        "verdict_engines": 2,
        "flagged_engines": 1,
        "malicious_engines": 1,
        "suspicious_engines": 0,
        "harmless_engines": 1,
        "undetected_engines": 0,
        "unsupported_engines": 0,
        "timeout_engines": 1,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "Excluded from percentage: 1 timed out",
    }
