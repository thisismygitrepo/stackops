import stat
from pathlib import Path

import pytest

from support.models import AutoRefreshUnavailableError, FileAgentSupport, RuntimeContext
from support.profiles import (
    copy_private_credential,
    find_refresh_profile,
    list_profile_directories,
    profile_credential,
    profile_root,
    select_named_profile,
)


def _resolve_test_credential(context: RuntimeContext) -> Path:
    destination_directory = context.home / ".test-agent"
    return destination_directory / "auth.json"


def _read_test_identity(path: Path) -> tuple[str, ...] | None:
    identity = path.read_text(encoding="utf-8").strip()
    if identity == "none":
        return None
    return (identity,)


def _file_support(identity_reader: bool) -> FileAgentSupport:
    return FileAgentSupport(
        agent="codex",
        display_name="Test Agent",
        aliases=("test",),
        backup_directory_name="test-agent",
        profile_file_name=Path("auth.json"),
        resolve_active_credential=_resolve_test_credential,
        read_identity=_read_test_identity if identity_reader else None,
        warning=None,
    )


def test_profile_paths_and_named_selection_are_deterministic(tmp_path: Path) -> None:
    support = _file_support(identity_reader=True)
    context = RuntimeContext(home=tmp_path, environment={}, system="Darwin")
    source_root = profile_root(support=support, context=context)
    profile_zulu = source_root / "Zulu"
    profile_alpha = source_root / "alpha"
    profile_zulu.mkdir(parents=True)
    profile_alpha.mkdir()

    profile_directories = list_profile_directories(source_root=source_root)

    assert profile_directories == [profile_alpha, profile_zulu]
    assert select_named_profile(profile_directories=profile_directories, profile_name="Zulu") == profile_zulu
    assert profile_credential(profile_directory=profile_alpha, support=support) == profile_alpha / "auth.json"


def test_copy_private_credential_replaces_file_and_hardens_permissions(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    destination = tmp_path / "active" / "auth.json"
    source.write_text("new credential", encoding="utf-8")
    source.chmod(0o644)
    destination.parent.mkdir()
    destination.write_text("old credential", encoding="utf-8")

    copy_private_credential(source=source, destination=destination)

    assert destination.read_text(encoding="utf-8") == "new credential"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert list(destination.parent.glob(".auth.json.*.tmp")) == []


def test_find_refresh_profile_matches_identity_and_ignores_unmatchable_profile(tmp_path: Path) -> None:
    support = _file_support(identity_reader=True)
    active_credential = tmp_path / "active.json"
    active_credential.write_text("account-one", encoding="utf-8")
    matching_profile = tmp_path / "matching"
    unmatchable_profile = tmp_path / "unmatchable"
    other_profile = tmp_path / "other"
    for profile_directory, identity in (
        (matching_profile, "account-one"),
        (unmatchable_profile, "none"),
        (other_profile, "account-two"),
    ):
        profile_directory.mkdir()
        (profile_directory / "auth.json").write_text(identity, encoding="utf-8")

    selected_profile = find_refresh_profile(
        support=support,
        profile_directories=[other_profile, unmatchable_profile, matching_profile],
        active_credential=active_credential,
    )

    assert selected_profile == matching_profile


def test_find_refresh_profile_rejects_automatic_refresh_without_identity(tmp_path: Path) -> None:
    support = _file_support(identity_reader=False)
    active_credential = tmp_path / "active.json"
    active_credential.write_text("account-one", encoding="utf-8")

    with pytest.raises(AutoRefreshUnavailableError, match="requires --profile"):
        find_refresh_profile(support=support, profile_directories=[], active_credential=active_credential)


def test_find_refresh_profile_rejects_duplicate_identity_matches(tmp_path: Path) -> None:
    support = _file_support(identity_reader=True)
    active_credential = tmp_path / "active.json"
    active_credential.write_text("account-one", encoding="utf-8")
    profile_directories = [tmp_path / "one", tmp_path / "two"]
    for profile_directory in profile_directories:
        profile_directory.mkdir()
        (profile_directory / "auth.json").write_text("account-one", encoding="utf-8")

    with pytest.raises(ValueError, match="Multiple codex backup profiles match"):
        find_refresh_profile(
            support=support,
            profile_directories=profile_directories,
            active_credential=active_credential,
        )

