import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner


def _load_pwdmgr_module():
    module_path = Path(__file__).resolve().parents[1] / "pwdmgr.py"
    spec = importlib.util.spec_from_file_location("pwdmgr_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pwdmgr_under_test"] = module
    spec.loader.exec_module(module)
    return module


pwdmgr = _load_pwdmgr_module()


def test_pwdmgr_cache_uses_stackops_gpg_helpers(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "tmp_results" / "cache" / "pwdmgr" / "cache.json.gpg"
    calls: list[tuple[str, bytes]] = []

    monkeypatch.setattr(pwdmgr, "CACHE_PATH", cache_path)

    def fake_encrypt(data: bytes) -> bytes:
        calls.append(("encrypt", data))
        return b"gpg:" + data

    def fake_decrypt(data: bytes) -> bytes:
        calls.append(("decrypt", data))
        assert data.startswith(b"gpg:")
        return data.removeprefix(b"gpg:")

    monkeypatch.setattr(pwdmgr, "encrypt_bytes_asymmetric", fake_encrypt)
    monkeypatch.setattr(pwdmgr, "decrypt_bytes_asymmetric", fake_decrypt)

    pwdmgr.save_encrypted_cache({"BW_SESSION": "session-token"})

    assert cache_path.read_bytes().startswith(b"gpg:")
    assert pwdmgr.load_encrypted_cache() == {"BW_SESSION": "session-token"}
    assert calls == [
        ("encrypt", b'{"BW_SESSION": "session-token"}'),
        ("decrypt", b'gpg:{"BW_SESSION": "session-token"}'),
    ]


def test_pwdmgr_clean_cache_removes_current_cache(monkeypatch, tmp_path: Path) -> None:
    tmp_results_root = tmp_path / "tmp_results"
    cache_path = tmp_results_root / "cache" / "pwdmgr" / "cache.json.gpg"

    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(b"gpg-cache")

    monkeypatch.setattr(pwdmgr, "TMP_RESULTS_ROOT", tmp_results_root)
    monkeypatch.setattr(pwdmgr, "CACHE_PATH", cache_path)

    pwdmgr.clean_cache()

    assert not cache_path.exists()


def test_pwdmgr_clean_cache_alias_runs_without_args_help(monkeypatch, tmp_path: Path) -> None:
    tmp_results_root = tmp_path / "tmp_results"
    cache_path = tmp_results_root / "cache" / "pwdmgr" / "cache.json.gpg"

    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(b"gpg-cache")

    monkeypatch.setattr(pwdmgr, "TMP_RESULTS_ROOT", tmp_results_root)
    monkeypatch.setattr(pwdmgr, "CACHE_PATH", cache_path)

    result = CliRunner().invoke(pwdmgr.app, ["c"])

    assert result.exit_code == 0
    assert not cache_path.exists()
    assert "Removed cached pwdmgr data." in result.output


def test_load_bitwarden_credentials_uses_stackops_search_secrets(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_search_secrets(
        *,
        path: Path,
        entry_name: str,
        profile: str,
        keys: tuple[str, str, str],
    ) -> list[dict[str, object]]:
        calls.append(
            {
                "path": path,
                "entry_name": entry_name,
                "profile": profile,
                "keys": keys,
            }
        )
        return [
            {
                "name": entry_name,
                "profile": profile,
                "secrets": [
                    {
                        "tags": ["bitwarden"],
                        "scopes": ["development"],
                        "keyValues": {
                            "BW_CLIENTID": "client-id",
                            "BW_CLIENTSECRET": "client-secret",
                            "BW_PASSWORD": "vault-password",
                        },
                    }
                ],
            }
        ]

    monkeypatch.setattr(pwdmgr, "search_secrets", fake_search_secrets)

    credentials = pwdmgr.load_bitwarden_credentials("bitwarden0", "dev")

    assert calls == [
        {
            "path": pwdmgr.SECRETS_DOFILE,
            "entry_name": "bitwarden0",
            "profile": "dev",
            "keys": ("BW_CLIENTID", "BW_CLIENTSECRET", "BW_PASSWORD"),
        }
    ]
    assert credentials == pwdmgr.BitwardenCredentials(
        entry_name="bitwarden0",
        profile="dev",
        client_id="client-id",
        client_secret="client-secret",
        password="vault-password",
    )


def test_login_and_unlock_requires_profile() -> None:
    result = CliRunner().invoke(pwdmgr.app, ["login-and-unlock", "--entry-name", "custom-entry"])

    assert result.exit_code != 0
    assert "Missing option '--profile'" in result.output


def test_login_and_unlock_defaults_entry_name(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    unlock_check_codes = iter((1, 0))
    persisted_sessions: list[str] = []

    def fake_load_bitwarden_credentials(entry_name: str, profile: str):
        calls.append((entry_name, profile))
        return pwdmgr.BitwardenCredentials(
            entry_name=entry_name,
            profile=profile,
            client_id="client-id",
            client_secret="client-secret",
            password="vault-password",
        )

    def fake_run_command(
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        assert env is not None
        assert env["BW_CLIENTID"] == "client-id"
        assert env["BW_CLIENTSECRET"] == "client-secret"
        assert env["BW_PASSWORD"] == "vault-password"

        if args == ["bw", "login", "--check"]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args == ["bw", "unlock", "--check"]:
            return subprocess.CompletedProcess(args, next(unlock_check_codes), stdout="", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    def fake_run_bw_command(args: list[str], *, env: dict[str, str] | None = None) -> str:
        assert args == ["bw", "unlock", "--passwordenv", "BW_PASSWORD", "--raw"]
        assert env is not None
        assert env["BW_CLIENTID"] == "client-id"
        assert env["BW_CLIENTSECRET"] == "client-secret"
        assert env["BW_PASSWORD"] == "vault-password"
        return "session-token\n"

    monkeypatch.setattr(pwdmgr, "load_bitwarden_credentials", fake_load_bitwarden_credentials)
    monkeypatch.setattr(pwdmgr, "load_session_token_from_cache", lambda: None)
    monkeypatch.setattr(pwdmgr, "persist_session_token_to_cache", persisted_sessions.append)
    monkeypatch.setattr(pwdmgr, "run_command", fake_run_command)
    monkeypatch.setattr(pwdmgr, "run_bw_command", fake_run_bw_command)
    monkeypatch.setenv("BW_CLIENTID", "")
    monkeypatch.setenv("BW_CLIENTSECRET", "")
    monkeypatch.setenv("BW_PASSWORD", "")
    monkeypatch.setenv("BW_SESSION", "")

    result = CliRunner().invoke(pwdmgr.app, ["login-and-unlock", "--profile", "dev"])

    assert result.exit_code == 0
    assert calls == [(pwdmgr.DEFAULT_BITWARDEN_ENTRY_NAME, "dev")]
    assert persisted_sessions == ["session-token"]


def test_login_and_unlock_accepts_short_profile_and_entry_name_option(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    persisted_sessions: list[str] = []

    def fake_load_bitwarden_credentials(entry_name: str, profile: str):
        calls.append((entry_name, profile))
        return pwdmgr.BitwardenCredentials(
            entry_name=entry_name,
            profile=profile,
            client_id="client-id",
            client_secret="client-secret",
            password="vault-password",
        )

    def fake_run_command(
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        assert env is not None
        assert env["BW_CLIENTID"] == "client-id"
        assert env["BW_CLIENTSECRET"] == "client-secret"
        assert env["BW_PASSWORD"] == "vault-password"
        assert env["BW_SESSION"] == "cached-session"

        if args in (["bw", "login", "--check"], ["bw", "unlock", "--check"]):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(pwdmgr, "load_bitwarden_credentials", fake_load_bitwarden_credentials)
    monkeypatch.setattr(pwdmgr, "load_session_token_from_cache", lambda: "cached-session")
    monkeypatch.setattr(pwdmgr, "persist_session_token_to_cache", persisted_sessions.append)
    monkeypatch.setattr(pwdmgr, "run_command", fake_run_command)

    result = CliRunner().invoke(pwdmgr.app, ["login-and-unlock", "--entry-name", "custom-entry", "-p", "dev"])

    assert result.exit_code == 0
    assert calls == [("custom-entry", "dev")]
    assert persisted_sessions == ["cached-session"]


def test_get_vault_status_includes_account_metadata(monkeypatch) -> None:
    expected_payload = {
        "status": "locked",
        "userEmail": "work@example.com",
        "userId": "user-123",
        "serverUrl": "https://vault.example.com",
    }

    def fake_run(args: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        assert args == ["bw", "status"]
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(expected_payload), stderr="")

    monkeypatch.setattr(pwdmgr.subprocess, "run", fake_run)

    vault_status = pwdmgr.get_vault_status()

    assert vault_status == pwdmgr.VaultStatus(
        status="locked",
        user_email="work@example.com",
        user_id="user-123",
        server_url="https://vault.example.com",
    )


def test_search_locked_reports_logged_in_account(monkeypatch) -> None:
    def fake_get_vault_status(_session: str | None = None) -> pwdmgr.VaultStatus:
        return pwdmgr.VaultStatus(
            status="locked",
            user_email="work@example.com",
            user_id="user-123",
            server_url="https://vault.example.com",
        )

    monkeypatch.setattr(pwdmgr, "load_session_token_from_cache", lambda: None)
    monkeypatch.setattr(pwdmgr, "get_vault_status", fake_get_vault_status)

    result = CliRunner().invoke(pwdmgr.app, ["search", "hi", "--fresh"])
    output = result.output.replace("\r\n", "\n")

    assert result.exit_code == 1
    assert "Vault is locked.\nAccount: work@example.com\nUser ID: user-123" in output
