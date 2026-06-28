from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import clean_agentops_cache


def test_clean_agentops_cache_removes_agentops_and_preserves_other_ai_content(tmp_path: Path) -> None:
    reports: list[str] = []
    iter_cache = tmp_path.joinpath(".ai", "agentops", "iterations", "alpha", "iter-001")
    iter_cache.mkdir(parents=True)
    iter_cache.joinpath("task.md").write_text("task", encoding="utf-8")
    parallel_contract = tmp_path.joinpath(".ai", "agentops", "parallel-agents", "contracts", "agents.json")
    parallel_contract.parent.mkdir(parents=True)
    parallel_contract.write_text("{}", encoding="utf-8")
    unrelated_ai_file = tmp_path.joinpath(".ai", "tmp_scripts", "keep.txt")
    unrelated_ai_file.parent.mkdir(parents=True)
    unrelated_ai_file.write_text("keep", encoding="utf-8")

    result = clean_agentops_cache(cwd=tmp_path, report=reports.append)

    assert result.removed is True
    assert result.removed_entries == 8
    assert result.cache_path == tmp_path.joinpath(".ai", "agentops")
    assert not tmp_path.joinpath(".ai", "agentops").exists()
    assert unrelated_ai_file.is_file()
    assert reports == ["Removed AgentOps cache at ./.ai/agentops (8 path(s))."]


def test_clean_agentops_cache_reports_missing_cache(tmp_path: Path) -> None:
    reports: list[str] = []

    result = clean_agentops_cache(cwd=tmp_path, report=reports.append)

    assert result.removed is False
    assert result.removed_entries == 0
    assert reports == ["No AgentOps cache found at ./.ai/agentops."]
