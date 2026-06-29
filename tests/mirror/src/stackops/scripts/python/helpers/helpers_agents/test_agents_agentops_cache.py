from pathlib import Path
from typing import Literal

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_agentops_cache
from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import clean_agentops_cache


def _create_run(*, iterations_path: Path, slug: str) -> Path:
    run_path = iterations_path.joinpath(slug)
    task_path = run_path.joinpath("iter-001", "task.md")
    task_path.parent.mkdir(parents=True)
    task_path.write_text("task", encoding="utf-8")
    return run_path


def test_clean_agentops_cache_removes_only_inactive_iteration_runs(tmp_path: Path) -> None:
    reports: list[str] = []
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    inactive_run = _create_run(iterations_path=iterations_path, slug="alpha")
    active_run = _create_run(iterations_path=iterations_path, slug="beta")
    unmanaged_entry = iterations_path.joinpath("notes.txt")
    unmanaged_entry.write_text("keep", encoding="utf-8")
    parallel_contract = tmp_path.joinpath(".ai", "agentops", "parallel-agents", "contracts", "agents.json")
    parallel_contract.parent.mkdir(parents=True)
    parallel_contract.write_text("{}", encoding="utf-8")

    result = clean_agentops_cache(
        cwd=tmp_path,
        dry_run=False,
        load_active_iter_workspace_labels=lambda: frozenset({"iter-beta"}),
        report=reports.append,
    )

    assert result.repo_root == tmp_path
    assert result.iterations_path == iterations_path
    assert result.removed_runs == (inactive_run,)
    assert result.protected_runs == (active_run,)
    assert result.unmanaged_entries == (unmanaged_entry,)
    assert result.removed_entries == 3
    assert result.dry_run is False
    assert result.removed is True
    assert not inactive_run.exists()
    assert active_run.is_dir()
    assert unmanaged_entry.is_file()
    assert parallel_contract.is_file()
    assert tmp_path.joinpath(".ai", "agentops").is_dir()
    assert any("Preserved unmanaged iteration entry" in report for report in reports)
    assert any("Protected active iteration run" in report for report in reports)


def test_clean_agentops_cache_rechecks_activity_before_each_deletion(tmp_path: Path) -> None:
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    alpha_run = _create_run(iterations_path=iterations_path, slug="alpha")
    beta_run = _create_run(iterations_path=iterations_path, slug="beta")
    active_snapshots = iter((frozenset(), frozenset(), frozenset({"iter-beta"})))
    load_calls = 0

    def load_active_iter_workspace_labels() -> frozenset[str]:
        nonlocal load_calls
        load_calls += 1
        return next(active_snapshots)

    result = clean_agentops_cache(
        cwd=tmp_path,
        dry_run=False,
        load_active_iter_workspace_labels=load_active_iter_workspace_labels,
        report=lambda _message: None,
    )

    assert load_calls == 3
    assert result.removed_runs == (alpha_run,)
    assert result.protected_runs == (beta_run,)
    assert not alpha_run.exists()
    assert beta_run.is_dir()


def test_clean_agentops_cache_dry_run_reports_planned_removal(tmp_path: Path) -> None:
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    run_path = _create_run(iterations_path=iterations_path, slug="alpha")

    result = clean_agentops_cache(
        cwd=tmp_path,
        dry_run=True,
        load_active_iter_workspace_labels=lambda: frozenset(),
        report=lambda _message: None,
    )

    assert result.removed_runs == (run_path,)
    assert result.removed_entries == 3
    assert result.dry_run is True
    assert result.removed is False
    assert run_path.is_dir()


def test_clean_agentops_cache_reports_missing_iterations_without_loading_activity(tmp_path: Path) -> None:
    load_called = False
    reports: list[str] = []

    def load_active_iter_workspace_labels() -> frozenset[str]:
        nonlocal load_called
        load_called = True
        return frozenset()

    result = clean_agentops_cache(
        cwd=tmp_path,
        dry_run=False,
        load_active_iter_workspace_labels=load_active_iter_workspace_labels,
        report=reports.append,
    )

    assert load_called is False
    assert result.iterations_path == tmp_path.joinpath(".ai", "agentops", "iterations")
    assert result.removed_runs == ()
    assert result.protected_runs == ()
    assert result.unmanaged_entries == ()
    assert result.removed_entries == 0
    assert reports == ["No AgentOps iteration records found at ./.ai/agentops/iterations."]


@pytest.mark.parametrize("symlink_level", ["ai", "agentops", "iterations", "run"])
def test_clean_agentops_cache_refuses_symlinks(
    tmp_path: Path,
    symlink_level: Literal["ai", "agentops", "iterations", "run"],
) -> None:
    external_path = tmp_path.joinpath("external", symlink_level)
    external_path.mkdir(parents=True)
    ai_path = tmp_path.joinpath(".ai")
    agentops_path = ai_path.joinpath("agentops")
    iterations_path = agentops_path.joinpath("iterations")
    match symlink_level:
        case "ai":
            ai_path.symlink_to(external_path, target_is_directory=True)
        case "agentops":
            ai_path.mkdir()
            agentops_path.symlink_to(external_path, target_is_directory=True)
        case "iterations":
            agentops_path.mkdir(parents=True)
            iterations_path.symlink_to(external_path, target_is_directory=True)
        case "run":
            iterations_path.mkdir(parents=True)
            iterations_path.joinpath("alpha").symlink_to(external_path, target_is_directory=True)

    with pytest.raises(RuntimeError, match="symlinked"):
        clean_agentops_cache(
            cwd=tmp_path,
            dry_run=False,
            load_active_iter_workspace_labels=lambda: frozenset(),
            report=lambda _message: None,
        )

    assert external_path.is_dir()


def test_clean_agentops_cache_refuses_non_directory_iterations_root(tmp_path: Path) -> None:
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    iterations_path.parent.mkdir(parents=True)
    iterations_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(RuntimeError, match="non-directory AgentOps iterations directory"):
        clean_agentops_cache(
            cwd=tmp_path,
            dry_run=False,
            load_active_iter_workspace_labels=lambda: frozenset(),
            report=lambda _message: None,
        )


def test_clean_agentops_cache_is_idempotent(tmp_path: Path) -> None:
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    run_path = _create_run(iterations_path=iterations_path, slug="alpha")

    def load_active() -> frozenset[str]:
        return frozenset()

    first_result = clean_agentops_cache(
        cwd=tmp_path,
        dry_run=False,
        load_active_iter_workspace_labels=load_active,
        report=lambda _message: None,
    )
    second_result = clean_agentops_cache(
        cwd=tmp_path,
        dry_run=False,
        load_active_iter_workspace_labels=load_active,
        report=lambda _message: None,
    )

    assert first_result.removed_runs == (run_path,)
    assert second_result.removed_runs == ()
    assert second_result.removed_entries == 0
    assert second_result.removed is False
    assert iterations_path.is_dir()


def test_clean_agentops_cache_wraps_filesystem_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    iterations_path = tmp_path.joinpath(".ai", "agentops", "iterations")
    _create_run(iterations_path=iterations_path, slug="alpha")

    def fail_rmtree(_path: Path) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(agents_agentops_cache.shutil, "rmtree", fail_rmtree)

    with pytest.raises(RuntimeError, match="Failed to clean AgentOps iteration records: denied"):
        clean_agentops_cache(
            cwd=tmp_path,
            dry_run=False,
            load_active_iter_workspace_labels=lambda: frozenset(),
            report=lambda _message: None,
        )
