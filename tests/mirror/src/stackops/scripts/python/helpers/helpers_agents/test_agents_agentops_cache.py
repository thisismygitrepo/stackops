import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_records
from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import clean_agentops_cache
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import WorkspaceId


def _write_run_manifest(*, run_path: Path, workspace_id: str, workspace_label: str) -> None:
    run_path.mkdir(parents=True)
    run_path.joinpath("run.json").write_text(
        json.dumps(
            {"schema_version": 1, "herdr_version": "0.7.3", "herdr_protocol": 16, "workspace_id": workspace_id, "workspace_label": workspace_label}
        ),
        encoding="utf-8",
    )


def test_clean_protects_current_run_by_stable_workspace_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_path = tmp_path.joinpath(".ai", "agentops", "iterations", "alpha")
    _write_run_manifest(run_path=run_path, workspace_id="w1", workspace_label="iter-renamed")

    def fake_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def active_ids() -> frozenset[WorkspaceId]:
        return frozenset((WorkspaceId("w1"),))

    monkeypatch.setattr(agents_iter_records, "get_repo_root", fake_repo_root)

    result = clean_agentops_cache(cwd=tmp_path, dry_run=False, load_active_workspace_ids=active_ids, report=lambda _message: None)

    assert result.protected_runs == (run_path,)
    assert result.removed_runs == ()
    assert run_path.exists()


def test_clean_removes_only_inactive_current_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    current_path = iterations_path.joinpath("current")
    legacy_path = iterations_path.joinpath("legacy")
    _write_run_manifest(run_path=current_path, workspace_id="w2", workspace_label="iter-current")
    legacy_path.mkdir(parents=True)

    def fake_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def no_active_ids() -> frozenset[WorkspaceId]:
        return frozenset()

    monkeypatch.setattr(agents_iter_records, "get_repo_root", fake_repo_root)

    result = clean_agentops_cache(cwd=tmp_path, dry_run=False, load_active_workspace_ids=no_active_ids, report=lambda _message: None)

    assert result.removed_runs == (current_path,)
    assert result.unmanaged_entries == (legacy_path,)
    assert not current_path.exists()
    assert legacy_path.exists()
