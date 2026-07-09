import base64
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents, ai_account
from stackops.scripts.python.helpers.helpers_ai_account.models import RuntimeContext


def _codex_auth(user_id: str, account_id: str, marker: str) -> str:
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


def test_hidden_aliases_retrieve_and_backup_in_opposite_directions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = RuntimeContext(home=tmp_path, environment={}, system="Darwin")
    monkeypatch.setattr(ai_account, "_runtime_context", lambda: context)
    saved_credential = tmp_path / "dotfiles" / "creds" / "llm" / "auggie" / "work" / "session.json"
    saved_credential.parent.mkdir(parents=True)
    saved_credential.write_text("saved", encoding="utf-8")
    active_credential = tmp_path / ".augment" / "session.json"
    runner = CliRunner()

    retrieve_result = runner.invoke(ai_account.app, ["r", "auggie", "--profile", "work"])

    assert retrieve_result.exit_code == 0, retrieve_result.output
    assert active_credential.read_text(encoding="utf-8") == "saved"

    active_credential.write_text("active", encoding="utf-8")
    backup_result = runner.invoke(ai_account.app, ["b", "auggie", "--profile", "work"])

    assert backup_result.exit_code == 0, backup_result.output
    assert saved_credential.read_text(encoding="utf-8") == "active"


def test_active_credential_override_bypasses_unavailable_default_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = RuntimeContext(home=tmp_path, environment={}, system="Darwin")
    monkeypatch.setattr(ai_account, "_runtime_context", lambda: context)
    saved_credential = tmp_path / "dotfiles" / "creds" / "llm" / "claude" / "work" / ".credentials.json"
    saved_credential.parent.mkdir(parents=True)
    saved_credential.write_text("saved", encoding="utf-8")
    active_credential = tmp_path / "custom" / ".credentials.json"

    result = CliRunner().invoke(
        ai_account.app,
        ["retrieve", "claude", "--profile", "work", "--active-credential", str(active_credential)],
    )

    assert result.exit_code == 0, result.output
    assert active_credential.read_text(encoding="utf-8") == "saved"


def test_backup_selects_the_unique_profile_matching_the_active_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = RuntimeContext(home=tmp_path, environment={}, system="Darwin")
    monkeypatch.setattr(ai_account, "_runtime_context", lambda: context)
    active_auth = _codex_auth(user_id="user-one", account_id="workspace-one", marker="active")
    matching_auth = _codex_auth(user_id="user-one", account_id="workspace-one", marker="saved")
    other_auth = _codex_auth(user_id="user-two", account_id="workspace-one", marker="other")
    active_credential = tmp_path / ".codex" / "auth.json"
    matching_credential = tmp_path / "dotfiles" / "creds" / "llm" / "codex" / "matching" / "auth.json"
    other_credential = tmp_path / "dotfiles" / "creds" / "llm" / "codex" / "other" / "auth.json"
    active_credential.parent.mkdir(parents=True)
    matching_credential.parent.mkdir(parents=True)
    other_credential.parent.mkdir(parents=True)
    active_credential.write_text(active_auth, encoding="utf-8")
    matching_credential.write_text(matching_auth, encoding="utf-8")
    other_credential.write_text(other_auth, encoding="utf-8")

    result = CliRunner().invoke(ai_account.app, ["backup", "codex"])

    assert result.exit_code == 0, result.output
    assert matching_credential.read_text(encoding="utf-8") == active_auth
    assert other_credential.read_text(encoding="utf-8") == other_auth


def test_account_help_requires_an_explicit_operation_and_removes_refresh() -> None:
    runner = CliRunner()

    account_help = runner.invoke(agents.get_app(), ["account", "--help"])
    alias_help = runner.invoke(agents.get_app(), ["A", "--help"])
    backup_alias_help = runner.invoke(agents.get_app(), ["account", "b", "--help"])
    retrieve_alias_help = runner.invoke(agents.get_app(), ["account", "r", "--help"])
    old_interface = runner.invoke(agents.get_app(), ["A", "codex", "--refresh"])

    assert account_help.exit_code == 0, account_help.output
    assert alias_help.exit_code == 0, alias_help.output
    assert backup_alias_help.exit_code == 0, backup_alias_help.output
    assert retrieve_alias_help.exit_code == 0, retrieve_alias_help.output
    assert "<b> Save an active credential to a profile" in account_help.output
    assert "<r> Retrieve a saved profile as the active credential" in account_help.output
    assert "--refresh" not in account_help.output
    assert old_interface.exit_code != 0
