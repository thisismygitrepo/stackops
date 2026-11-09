import base64
import hashlib
import json
import secrets
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import cast
from urllib.parse import parse_qs, urlparse

import requests

from stackops.scripts.python.helpers.helpers_agents.constants import (
    T3_FULL_ACCESS_SCOPES,
    T3_HTTP_TIMEOUT_SECONDS,
    T3_MCP_PROTOCOL_VERSION,
    T3_OAUTH_REDIRECT_URI,
    T3_PAIRING_TTL,
    T3_RUNTIME_MODE,
    T3_SERVER_URL,
)

type JsonObject = dict[str, object]


@dataclass(frozen=True)
class T3McpSession:
    headers: dict[str, str]


def require_t3_object(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        raise RuntimeError(f"""T3 Code returned a non-object for {context}: {value!r}""")
    return cast(JsonObject, value)


def require_t3_text(mapping: JsonObject, key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"""T3 Code {context} has no "{key}": {mapping!r}""")
    return value


def _run_t3_json(arguments: list[str]) -> object:
    completed = subprocess.run(["t3", *arguments], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def _post_json(path: str, payload: JsonObject) -> JsonObject:
    response = requests.post(f"""{T3_SERVER_URL}{path}""", json=payload, timeout=T3_HTTP_TIMEOUT_SECONDS)
    if not response.ok:
        raise RuntimeError(f"""T3 Code {path} failed with HTTP {response.status_code}: {response.text}""")
    return require_t3_object(response.json(), path)


def _issue_full_access_token(client_name: str) -> str:
    scope_arguments = [argument for scope in T3_FULL_ACCESS_SCOPES for argument in ("--scope", scope)]
    pairing = require_t3_object(
        _run_t3_json(["auth", "pairing", "create", *scope_arguments, "--ttl", T3_PAIRING_TTL, "--label", client_name, "--json"]),
        "auth pairing create",
    )
    registration = _post_json("/oauth/mcp/register", {"client_name": client_name, "redirect_uris": [T3_OAUTH_REDIRECT_URI]})
    client_id = require_t3_text(registration, "client_id", "client registration")
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    resource = f"""{T3_SERVER_URL}/mcp"""
    authorization: JsonObject = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": T3_OAUTH_REDIRECT_URI,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": client_name,
        "resource": resource,
    }
    pairing_code = require_t3_text(pairing, "credential", "pairing credential")
    decision = _post_json(
        "/oauth/mcp/decision",
        {"authorization": authorization, "decision": {"_tag": "pairing-code", "access": T3_RUNTIME_MODE, "code": pairing_code}},
    )
    codes = parse_qs(urlparse(require_t3_text(decision, "redirectTo", "approval decision")).query).get("code")
    if codes is None or len(codes) != 1:
        raise RuntimeError("T3 Code approval did not return an authorization code.")
    token_response = requests.post(
        f"""{T3_SERVER_URL}/oauth/mcp/token""",
        data={
            "grant_type": "authorization_code",
            "code": codes[0],
            "redirect_uri": T3_OAUTH_REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": resource,
        },
        timeout=T3_HTTP_TIMEOUT_SECONDS,
    )
    if not token_response.ok:
        raise RuntimeError(f"""T3 Code token exchange failed with HTTP {token_response.status_code}: {token_response.text}""")
    return require_t3_text(require_t3_object(token_response.json(), "token exchange"), "access_token", "token exchange")


def _revoke_client_sessions(client_name: str) -> None:
    sessions = _run_t3_json(["auth", "session", "list", "--json"])
    if not isinstance(sessions, list):
        raise RuntimeError(f"""t3 auth session list returned a non-list: {sessions!r}""")
    for entry in cast(list[object], sessions):
        session = require_t3_object(entry, "auth session")
        client = session.get("client")
        if session.get("subject") == "mcp-client" and isinstance(client, dict) and cast(JsonObject, client).get("label") == client_name:
            session_id = require_t3_text(session, "sessionId", "auth session")
            subprocess.run(["t3", "auth", "session", "revoke", session_id], check=True, capture_output=True, text=True)


def _post_mcp(headers: dict[str, str], message: JsonObject) -> requests.Response:
    response = requests.post(f"""{T3_SERVER_URL}/mcp""", headers=headers, json=message, timeout=T3_HTTP_TIMEOUT_SECONDS)
    if not response.ok:
        raise RuntimeError(f"""T3 Code MCP request {message.get("method")} failed with HTTP {response.status_code}: {response.text}""")
    return response


def _initialize(token: str) -> T3McpSession:
    headers = {
        "Authorization": f"""Bearer {token}""",
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": T3_MCP_PROTOCOL_VERSION,
    }
    initialize: JsonObject = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": T3_MCP_PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "stackops", "version": "1"}},
    }
    session_headers = {**headers, "mcp-session-id": _post_mcp(headers=headers, message=initialize).headers["mcp-session-id"]}
    _post_mcp(headers=session_headers, message={"jsonrpc": "2.0", "method": "notifications/initialized"})
    return T3McpSession(headers=session_headers)


@contextmanager
def open_t3_mcp_session() -> Generator[T3McpSession]:
    client_name = f"""stackops-{secrets.token_hex(4)}"""
    token = _issue_full_access_token(client_name=client_name)
    try:
        yield _initialize(token=token)
    finally:
        _revoke_client_sessions(client_name=client_name)


def call_t3_tool(session: T3McpSession, name: str, arguments: JsonObject) -> JsonObject:
    message: JsonObject = {"jsonrpc": "2.0", "id": secrets.token_hex(4), "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    response = _post_mcp(headers=session.headers, message=message)
    body = response.content.decode("utf-8")
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        body = [line.removeprefix("data: ") for line in body.splitlines() if line.startswith("data: ")][-1]
    envelope = require_t3_object(json.loads(body), f"""tool {name}""")
    if "error" in envelope:
        raise RuntimeError(f"""T3 Code tool {name} failed: {envelope["error"]!r}""")
    result = require_t3_object(envelope.get("result"), f"""tool {name} result""")
    if result.get("isError") is True:
        raise RuntimeError(f"""T3 Code tool {name} failed: {json.dumps(result.get("content"))}""")
    return require_t3_object(result.get("structuredContent"), f"""tool {name} structured content""")
