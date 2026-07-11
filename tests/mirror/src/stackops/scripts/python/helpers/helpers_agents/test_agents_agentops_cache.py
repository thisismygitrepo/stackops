import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_records
from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import clean_agentops_cache
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import WorkspaceId


def _write_run_manifest(*, run_path: Path, herdr_session: str, workspace_id: str, workspace_label: str) -> None:
    run_path.mkdir(parents=True)
    run_path.joinpath("run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "herdr_version": "0.7.3",
                "herdr_protocol": 16,
                "herdr_session": herdr_session,
                "workspace_id": workspace_id,
                "workspace_label": workspace_label,
            }
        ),
        encoding="utf-8",
    )


def test_clean_protects_current_run_by_stable_workspace_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    run_path = tmp_path.joinpath(".ai", "agentops", "iterations", "alpha")
    _write_run_manifest(run_path=run_path, herdr_session="default", workspace_id="w1", workspace_label="iter-renamed")

    def fake_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def active_ids() -> frozenset[WorkspaceId]:
        return frozenset((WorkspaceId("w1"),))

    monkeypatch.setattr(agents_iter_records, "get_repo_root", fake_repo_root)

    result = clean_agentops_cache(cwd=tmp_path, workspace_id=None, dry_run=False, load_active_workspace_ids=active_ids, report=lambda _message: None)

    assert result.protected_runs == (run_path,)
    assert result.removed_runs == ()
    assert run_path.exists()


def test_clean_removes_only_inactive_current_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    current_path = iterations_path.joinpath("current")
    legacy_path = iterations_path.joinpath("legacy")
    named_session_path = iterations_path.joinpath("named-session")
    _write_run_manifest(run_path=current_path, herdr_session="default", workspace_id="w2", workspace_label="iter-current")
    _write_run_manifest(run_path=named_session_path, herdr_session="work", workspace_id="w3", workspace_label="iter-named")
    legacy_path.mkdir(parents=True)

    def fake_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def no_active_ids() -> frozenset[WorkspaceId]:
        return frozenset()

    monkeypatch.setattr(agents_iter_records, "get_repo_root", fake_repo_root)

    result = clean_agentops_cache(
        cwd=tmp_path, workspace_id=None, dry_run=False, load_active_workspace_ids=no_active_ids, report=lambda _message: None
    )

    assert result.removed_runs == (current_path,)
    assert result.unmanaged_entries == (legacy_path, named_session_path)
    assert not current_path.exists()
    assert legacy_path.exists()
    assert named_session_path.exists()


def test_clean_scopes_removal_to_one_inactive_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    selected_path = iterations_path.joinpath("selected")
    unselected_path = iterations_path.joinpath("unselected")
    _write_run_manifest(run_path=selected_path, herdr_session="default", workspace_id="w1", workspace_label="iter-selected")
    _write_run_manifest(run_path=unselected_path, herdr_session="default", workspace_id="w2", workspace_label="iter-unselected")

    def fake_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def no_active_ids() -> frozenset[WorkspaceId]:
        return frozenset()

    monkeypatch.setattr(agents_iter_records, "get_repo_root", fake_repo_root)

    result = clean_agentops_cache(
        cwd=tmp_path, workspace_id=WorkspaceId("w1"), dry_run=False, load_active_workspace_ids=no_active_ids, report=lambda _message: None
    )

    assert result.removed_runs == (selected_path,)
    assert not selected_path.exists()
    assert unselected_path.exists()


def test_clean_rejects_unknown_workspace_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    run_path = tmp_path.joinpath(".ai", "agentops", "iterations", "alpha")
    _write_run_manifest(run_path=run_path, herdr_session="default", workspace_id="w1", workspace_label="iter-alpha")

    def fake_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def no_active_ids() -> frozenset[WorkspaceId]:
        return frozenset()

    monkeypatch.setattr(agents_iter_records, "get_repo_root", fake_repo_root)

    with pytest.raises(RuntimeError, match="workspace ID 'missing'"):
        clean_agentops_cache(
            cwd=tmp_path, workspace_id=WorkspaceId("missing"), dry_run=False, load_active_workspace_ids=no_active_ids, report=lambda _message: None
        )


def test_clean_repository_error_is_specific_to_record_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_repo_root(_cwd: Path) -> None:
        return None

    def no_active_ids() -> frozenset[WorkspaceId]:
        return frozenset()

    monkeypatch.setattr(agents_iter_records, "get_repo_root", no_repo_root)

    with pytest.raises(RuntimeError) as error:
        clean_agentops_cache(cwd=tmp_path, workspace_id=None, dry_run=False, load_active_workspace_ids=no_active_ids, report=lambda _message: None)

    assert str(error.value) == f"AgentOps clean requires a Git repository; none contains {tmp_path.resolve()}."
