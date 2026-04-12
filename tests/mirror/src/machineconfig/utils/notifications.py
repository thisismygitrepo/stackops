from __future__ import annotations

from dataclasses import dataclass, field
from email.message import Message
from pathlib import Path
from types import ModuleType
import sys
import smtplib

import pytest

from machineconfig.utils import notifications as notifications_module


@dataclass(slots=True)
class _FakeResponse:
    text: str


@dataclass(slots=True)
class _FakeServer:
    host: str
    port: int
    login_calls: list[tuple[str, str]] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    quit_called: bool = False

    def login(self, email_add: str, password: str) -> None:
        self.login_calls.append((email_add, password))

    def send_message(self, message: Message) -> None:
        self.messages.append(message)

    def sendmail(self, from_addr: str, to_addrs: str, msg: str) -> dict[str, tuple[int, bytes]]:
        _ = from_addr, to_addrs, msg
        return {}

    def quit(self) -> None:
        self.quit_called = True


def test_download_to_memory_normalizes_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    requests_module = ModuleType("requests")

    def fake_get(
        url: str,
        *,
        allow_redirects: bool,
        timeout: float | None,
        params: object,
    ) -> _FakeResponse:
        captured["url"] = url
        captured["allow_redirects"] = allow_redirects
        captured["timeout"] = timeout
        captured["params"] = params
        return _FakeResponse(text="ok")

    setattr(requests_module, "get", fake_get)
    monkeypatch.setitem(sys.modules, "requests", requests_module)

    response = notifications_module.download_to_memory(
        Path("https:/example.com/docs.md"),
        allow_redirects=False,
        timeout=2.5,
        params={"q": "demo"},
    )

    assert response.text == "ok"
    assert captured["url"] == "https://example.com/docs.md"
    assert captured["allow_redirects"] is False
    assert captured["timeout"] == 2.5
    assert captured["params"] == {"q": "demo"}


def test_md2html_wraps_markdown_in_html_document() -> None:
    html = notifications_module.md2html("# Title\n\nBody")

    assert "<!DOCTYPE html>" in html
    assert '<div class="markdown-body">' in html
    assert "Title" in html
    assert "Body" in html


def test_email_uses_ssl_server_and_sends_html_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_servers: list[_FakeServer] = []

    def fake_smtp_ssl(host: str, port: int) -> _FakeServer:
        server = _FakeServer(host=host, port=port)
        created_servers.append(server)
        return server

    def fail_if_plain_smtp(host: str, port: int) -> _FakeServer:
        raise AssertionError(f"Unexpected plain SMTP call: {(host, port)}")

    monkeypatch.setattr(smtplib, "SMTP_SSL", fake_smtp_ssl)
    monkeypatch.setattr(smtplib, "SMTP", fail_if_plain_smtp)
    monkeypatch.setattr(
        notifications_module,
        "md2html",
        lambda body: f"<html>{body}</html>",
    )

    config = {
        "email_add": "from@example.com",
        "password": "secret",
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "encryption": "ssl",
    }

    email = notifications_module.Email(config=config)
    email.send_message(
        to="to@example.com",
        subject="Hi",
        body="Body",
        txt_to_html=True,
    )
    email.close()

    assert len(created_servers) == 1
    server = created_servers[0]
    assert server.login_calls == [("from@example.com", "secret")]
    assert len(server.messages) == 1
    assert server.messages[0]["To"] == "to@example.com"

    payload_obj = server.messages[0].get_payload()
    assert isinstance(payload_obj, list)
    payload_text = str(payload_obj[0].get_payload())
    assert payload_text.startswith("<html>")
    assert "automated email sent via machineconfig.comms script" in payload_text
    assert server.quit_called is True
