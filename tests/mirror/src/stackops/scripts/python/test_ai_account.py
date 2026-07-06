import base64
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import ai_account
from stackops.scripts.python.helpers.helpers_ai_account.models import RuntimeContext


def _runtime_context(home: Path) -> RuntimeContext:
    return RuntimeContext(home=home, environment={}, system="Darwin")


def _codex_auth(*, user_id: str, account_id: str, marker: str) -> str:
    payload = {
        "https://api.openai.com/auth": {
            "chatgpt_user_id": user_id,
            "chatgpt_account_id": account_id,
        }
    }
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return json.dumps(
        {
            "tokens": {
                "id_token": f"header.{encoded_payload}.signature",
                "account_id": account_id,
            },
            "marker": marker,
        }
    )


def test_cli_installs_and_explicitly_refreshes_install_only_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = _runtime_context(home=tmp_path)
    monkeypatch.setattr(ai_account, "_runtime_context", lambda: context)
    profile_credential = tmp_path / "dotfiles" / "creds" / "llm" / "auggie" / "work" / "session.json"
    profile_credential.parent.mkdir(parents=True)
    profile_credential.write_text("backup", encoding="utf-8")
    runner = CliRunner()

    install_result = runner.invoke(ai_account.app, ["auggie", "--profile", "work"])

    active_credential = tmp_path / ".augment" / "session.json"
    assert install_result.exit_code == 0
    assert active_credential.read_text(encoding="utf-8") == "backup"

    active_credential.write_text("refreshed", encoding="utf-8")
    refresh_result = runner.invoke(ai_account.app, ["auggie", "--refresh", "--profile", "work"])

    assert refresh_result.exit_code == 0
    assert profile_credential.read_text(encoding="utf-8") == "refreshed"


def test_cli_auto_refreshes_codex_by_composite_user_and_workspace_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = _runtime_context(home=tmp_path)
    monkeypatch.setattr(ai_account, "_runtime_context", lambda: context)
    active_credential = tmp_path / ".codex" / "auth.json"
    active_credential.parent.mkdir()
    active_credential.write_text(
        _codex_auth(user_id="user-one", account_id="workspace-one", marker="active"),
        encoding="utf-8",
    )
    profile_root = tmp_path / "dotfiles" / "creds" / "llm" / "codex"
    matching_credential = profile_root / "matching" / "auth.json"
    other_credential = profile_root / "other" / "auth.json"
    matching_credential.parent.mkdir(parents=True)
    other_credential.parent.mkdir(parents=True)
    matching_credential.write_text(
        _codex_auth(user_id="user-one", account_id="workspace-one", marker="old"),
        encoding="utf-8",
    )
    other_credential.write_text(
        _codex_auth(user_id="user-two", account_id="workspace-one", marker="other"),
        encoding="utf-8",
    )

    result = CliRunner().invoke(ai_account.app, ["x", "--refresh"])

    assert result.exit_code == 0
    assert json.loads(matching_credential.read_text(encoding="utf-8"))["marker"] == "active"
    assert json.loads(other_credential.read_text(encoding="utf-8"))["marker"] == "other"


def test_cli_reports_managed_login_agent_without_accessing_profile_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_account, "_runtime_context", lambda: _runtime_context(home=tmp_path))

    result = CliRunner().invoke(ai_account.app, ["antigravity"])

    assert result.exit_code == 1
    assert "not file-profile-backed" in result.output
    assert not (tmp_path / "dotfiles").exists()


def test_cli_rejects_unknown_agent() -> None:
    result = CliRunner().invoke(ai_account.app, ["unknown-agent"])

    assert result.exit_code == 2
    assert "Unsupported agent" in result.output
