import base64
import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_ai_account.auggie import SUPPORT as AUGGIE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.claude import SUPPORT as CLAUDE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.cline import SUPPORT as CLINE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.codex import SUPPORT as CODEX_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.crush import SUPPORT as CRUSH_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.cursor_agent import SUPPORT as CURSOR_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.forge import SUPPORT as FORGE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.kilocode import SUPPORT as KILOCODE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.models import CredentialStorageUnavailableError, FileAgentSupport, RuntimeContext
from stackops.scripts.python.helpers.helpers_ai_account.opencode import SUPPORT as OPENCODE_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.pi import SUPPORT as PI_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.q import SUPPORT as Q_SUPPORT
from stackops.scripts.python.helpers.helpers_ai_account.qwen import SUPPORT as QWEN_SUPPORT


@pytest.mark.parametrize(
    ("support", "environment", "system", "expected_relative_path"),
    [
        (AUGGIE_SUPPORT, {}, "Darwin", Path(".augment/session.json")),
        (QWEN_SUPPORT, {}, "Darwin", Path(".qwen/settings.json")),
        (CODEX_SUPPORT, {}, "Darwin", Path(".codex/auth.json")),
        (CRUSH_SUPPORT, {}, "Darwin", Path(".local/share/crush/crush.json")),
        (Q_SUPPORT, {}, "Darwin", Path("Library/Application Support/amazon-q/data.sqlite3")),
        (OPENCODE_SUPPORT, {}, "Linux", Path(".local/share/opencode/auth.json")),
        (KILOCODE_SUPPORT, {}, "Linux", Path(".local/share/kilo/auth.json")),
        (CLINE_SUPPORT, {}, "Linux", Path(".cline/data/settings/providers.json")),
        (PI_SUPPORT, {}, "Darwin", Path(".pi/agent/auth.json")),
    ],
)
def test_default_file_agent_paths(
    tmp_path: Path,
    support: FileAgentSupport,
    environment: dict[str, str],
    system: str,
    expected_relative_path: Path,
) -> None:
    context = RuntimeContext(home=tmp_path, environment=environment, system=system)

    assert support.resolve_active_credential(context) == tmp_path / expected_relative_path


def test_documented_path_overrides_are_resolved(tmp_path: Path) -> None:
    override_root = tmp_path / "overrides"
    contexts_and_paths = (
        (
            CODEX_SUPPORT,
            RuntimeContext(home=tmp_path, environment={"CODEX_HOME": str(override_root / "codex")}, system="Darwin"),
            override_root / "codex" / "auth.json",
        ),
        (
            QWEN_SUPPORT,
            RuntimeContext(home=tmp_path, environment={"QWEN_HOME": str(override_root / "qwen")}, system="Darwin"),
            override_root / "qwen" / "settings.json",
        ),
        (
            CRUSH_SUPPORT,
            RuntimeContext(home=tmp_path, environment={"CRUSH_GLOBAL_DATA": str(override_root / "crush")}, system="Darwin"),
            override_root / "crush" / "crush.json",
        ),
        (
            OPENCODE_SUPPORT,
            RuntimeContext(home=tmp_path, environment={"XDG_DATA_HOME": str(override_root / "data")}, system="Linux"),
            override_root / "data" / "opencode" / "auth.json",
        ),
        (
            KILOCODE_SUPPORT,
            RuntimeContext(home=tmp_path, environment={"XDG_DATA_HOME": str(override_root / "data")}, system="Linux"),
            override_root / "data" / "kilo" / "auth.json",
        ),
        (
            CLINE_SUPPORT,
            RuntimeContext(
                home=tmp_path,
                environment={"CLINE_PROVIDER_SETTINGS_PATH": str(override_root / "cline.json")},
                system="Linux",
            ),
            override_root / "cline.json",
        ),
        (
            PI_SUPPORT,
            RuntimeContext(home=tmp_path, environment={"PI_CODING_AGENT_DIR": str(override_root / "pi")}, system="Darwin"),
            override_root / "pi" / "auth.json",
        ),
    )

    for support, context, expected_path in contexts_and_paths:
        assert support.resolve_active_credential(context) == expected_path


def test_forge_preserves_verified_legacy_path_precedence(tmp_path: Path) -> None:
    context = RuntimeContext(home=tmp_path, environment={}, system="Darwin")
    default_path = tmp_path / ".forge" / ".credentials.json"
    legacy_directory = tmp_path / "forge"

    assert FORGE_SUPPORT.resolve_active_credential(context) == default_path

    legacy_directory.mkdir()

    assert FORGE_SUPPORT.resolve_active_credential(context) == legacy_directory / ".credentials.json"


def test_platform_conditional_agents_reject_default_macos_keychain_storage(tmp_path: Path) -> None:
    macos_context = RuntimeContext(home=tmp_path, environment={}, system="Darwin")

    with pytest.raises(CredentialStorageUnavailableError, match="Keychain"):
        CLAUDE_SUPPORT.resolve_active_credential(macos_context)
    with pytest.raises(CredentialStorageUnavailableError, match="Keychain"):
        CURSOR_SUPPORT.resolve_active_credential(macos_context)

    cursor_file_context = RuntimeContext(
        home=tmp_path,
        environment={"AGENT_CLI_CREDENTIAL_STORE": "file"},
        system="Darwin",
    )
    assert CURSOR_SUPPORT.resolve_active_credential(cursor_file_context) == tmp_path / ".cursor" / "auth.json"


def test_cursor_file_profile_identity_uses_jwt_subject(tmp_path: Path) -> None:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "cursor-user"}).encode()).decode().rstrip("=")
    credential_path = tmp_path / "auth.json"
    credential_path.write_text(json.dumps({"accessToken": f"header.{payload}.signature"}), encoding="utf-8")
    identity_reader = CURSOR_SUPPORT.read_identity

    assert identity_reader is not None
    assert identity_reader(credential_path) == ("cursor-user",)


def test_cline_auto_identity_is_limited_to_oauth_account(tmp_path: Path) -> None:
    credential_path = tmp_path / "providers.json"
    oauth_document = {
        "version": 1,
        "providers": {
            "cline": {
                "tokenSource": "oauth",
                "settings": {"provider": "cline", "auth": {"accountId": "cline-user"}},
            }
        },
    }
    credential_path.write_text(json.dumps(oauth_document), encoding="utf-8")
    identity_reader = CLINE_SUPPORT.read_identity

    assert identity_reader is not None
    assert identity_reader(credential_path) == ("cline-user",)

    manual_document = {
        "version": 1,
        "providers": {
            "cline": {
                "tokenSource": "manual",
                "settings": {"provider": "cline", "auth": {"accountId": "cline-user"}},
            }
        },
    }
    credential_path.write_text(json.dumps(manual_document), encoding="utf-8")

    assert identity_reader(credential_path) is None


def test_pi_requires_explicit_profile_for_whole_store_refresh() -> None:
    assert PI_SUPPORT.read_identity is None
